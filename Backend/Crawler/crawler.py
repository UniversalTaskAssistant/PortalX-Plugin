import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import os
from os.path import join as pjoin
from datetime import datetime
from urllib.parse import urlparse, quote
import base64

class Spider(scrapy.Spider):
    """
    Scrapy spider for crawling websites and saving cleaned HTML content.
    Args:
        start_urls (list): Initial URLs to start crawling from
        company_name (str): Name of the company being crawled
        domain_limit (str): Optional domain restriction for crawling
    """
    name = 'UTASpider'
    
    def __init__(self, output_dir, start_urls=['https://www.bmw.com/en-au/index.html'], company_name='bmw', domain_limit=None,
                  *args, **kwargs):
        super(Spider, self).__init__(*args, **kwargs)
        self.name = company_name
        self.start_urls = start_urls 
        self.company_name = company_name 
        self.domain_limit = domain_limit

        self.max_depth = 5
        self.max_urls_per_domain = 1000

        self.domain_urls = {}
        self.visited_urls = set()
        self.failed_urls = set()
        self.all_urls = set()

        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = pjoin(output_dir, self.company_name)
        os.makedirs(self.output_dir, exist_ok=True)

    """
    ********************
    *** Main parsing ***
    ********************
    """
    def parse(self, response, depth=0):
        """
        Main parsing function that processes each webpage and extracts links.
        Args:
            response (scrapy.Response): The response object containing the webpage
            depth (int): Current depth level of crawling
        Returns:
            Generator of scrapy.Request objects for found URLs
        """
        # Check if max urls per domain reached
        if depth >= self.max_depth:
            return
        # Skip if not a valid URL
        if not self.is_valid_url(response.url):
            return
        # Check if max urls per domain reached
        domain = urlparse(response.url).netloc
        if domain not in self.domain_urls:
            self.domain_urls[domain] = 0
        if self.domain_urls[domain] >= self.max_urls_per_domain:
            return
        self.visited_urls.add(response.url)
        self.domain_urls[domain] += 1
        
        # Process and save current page
        try:
            print(f'\n*** Processing {response.url} ({len(self.visited_urls)}) ***')
            soup = self.clean_html(response)
            self.save_page_content(response.url, soup)
            
            # Extract and follow links
            for link in response.css('a::attr(href)').getall():
                # Ignore page anchor
                if not self.is_valid_url(link):
                    continue
                absolute_url = response.urljoin(link)
                self.all_urls.add(absolute_url)
                # Scrape the next page if it's valid
                if self.should_follow(absolute_url):
                    yield scrapy.Request(
                        absolute_url,
                        callback=self.parse,
                        cb_kwargs={'depth': depth + 1},
                        errback=self.handle_error
                    )
            # Save all links (moved to spider_closed)
            self.save_all_links()
        except Exception as e:
            self.logger.error(f'!!!Error processing {response.url}: {e} !!!')
            self.failed_urls.add((response.url, str(e)))
            self.save_failed_urls()

    """
    *********************
    *** HTML cleaning ***
    *********************
    """
    def clean_html(self, response):
        """
        Cleans and simplifies HTML content by removing unnecessary elements and attributes.
        Args:
            response (scrapy.Response): The response object containing the webpage
        Returns:
            BeautifulSoup: Cleaned HTML soup object
        """
        soup = BeautifulSoup(response.text, 'html.parser')
        # Clean head section
        head = soup.find('head')
        if head:
            # Remove all elements from head except title
            for tag in head.find_all():
                if tag.name != 'title':
                    tag.decompose()
        # Add source URL and title stamp at the beginning of body
        body = soup.find('body')
        if body:
            title_text = soup.find('title').string if soup.find('title') else "No title"
            stamp_html = f'''
            <div>
                <h1>Source URL: <a href="{response.url}">{response.url}</a>
                <br>Title: {title_text}</h1>
                <hr>
            </div>
            '''
            body.insert(0, BeautifulSoup(stamp_html, 'html.parser'))

        # Clean elements
        for tag in soup.find_all(['script', 'style', 'source']):
            tag.decompose()
        # Remove unused attributes
        allowed_attrs = ['href', 'src', 'aria-label']
        for tag in soup.find_all():
            # Special handling for <i> tags
            if tag.name == 'i':
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in allowed_attrs + ['class', 'data-icon']:
                        del tag[attr]
            else:
                attrs = dict(tag.attrs)
                for attr in attrs:
                    if attr not in allowed_attrs:
                        del tag[attr]

        # Remove redundant divs
        self.remove_redundant_divs(soup)
        return soup

    def remove_redundant_divs(self, soup):
        """
        Removes unnecessary nested div elements from HTML.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
        Returns:
            None (modifies soup object in place)
        """
        while True:
            redundant_found = False
            for div in soup.find_all('div'):
                # Get all children, excluding empty whitespace
                children = list(div.children)
                children = [c for c in children if not isinstance(c, str) or c.strip()]
                # Remove div if it's empty or has only one child
                if len(children) == 0:
                    div.decompose()
                    redundant_found = True
                    break
                elif len(children) == 1:
                    div.replace_with(children[0])
                    redundant_found = True
                    break
            if not redundant_found:
                break

    """
    *********************
    *** URL filtering ***
    *********************
    """
    def is_valid_url(self, url):
        """
        Checks if a URL should be processed based on domain restrictions.
        Args:
            url (str): URL to validate
        Returns:
            bool: True if URL is valid, False otherwise
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        if url.startswith('#'):
            return False
        if domain and self.domain_limit and self.domain_limit not in url:
            return False
        return True

    def should_follow(self, url):
        """
        Determines if a URL should be crawled based on various criteria.
        Args:
            url (str): URL to evaluate
        Returns:
            bool: True if URL should be followed, False otherwise
        """
        parsed = urlparse(url)
        domain = parsed.netloc
        # Skip if already visited
        if url in self.visited_urls:
            return False
        # Skip if not a valid URL
        if not url.startswith(('http://', 'https://')):
            return False
        # Skip if max urls per domain reached
        if domain in self.domain_urls and self.domain_urls[domain] >= self.max_urls_per_domain:
            return False
        # Skip if file extension
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
        return True

    def handle_error(self, failure):
        """
        Handles failed requests during crawling.
        Args:
            failure (Failure): The failure object containing error details
        Returns:
            None
        """
        self.logger.error(f'Request failed: {failure.request.url}')

    """
    *******************
    *** File saving ***
    *******************
    """
    def filename_from_url(self, url):
        """
        Generates a filesystem-safe filename from a URL.
        Args:
            url (str): URL to convert to filename
        Returns:
            str: Path where the file should be saved
        """
        # Parse URL and create domain directory
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        domain_dir = f'{self.output_dir}/{domain}'
        
        # Create path for file
        path = parsed_url.path
        if not path or path == '/':
            path = 'index'
        else:
            path = path.strip('/')
        # Add query string if it exists, with safe encoding
        if parsed_url.query:
            encoded_query = base64.urlsafe_b64encode(parsed_url.query.encode()).decode()
            path = f'{path}_{encoded_query}'
            
        # Create full directory path and ensure it exists
        full_path = f'{domain_dir}/{path}'.replace('.html', '')
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def save_page_content(self, url, soup):
        """
        Saves cleaned HTML content to a file.
        Args:
            url (str): Source URL of the content
            soup (BeautifulSoup): Cleaned HTML content
        Returns:
            None
        """
        # Get the filename from the URL
        file_path = f'{self.filename_from_url(url)}.html'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f'Saved cleaned HTML to {file_path}')

    def save_all_links(self):
        """
        Saves all discovered and visited URLs to JSON files.
        Args:
            None
        Returns:
            None
        """
        all_links_data = {
            'company_name': self.company_name,
            'crawl_time': datetime.now().isoformat(),
            'links_count': len(self.all_urls),
            'links': list(self.all_urls)
        }
        visited_urls_data = {
            'company_name': self.company_name,
            'crawl_time': datetime.now().isoformat(),
            'visited_urls_count': len(self.visited_urls),
            'visited_urls': list(self.visited_urls)
        }
        with open(f'{self.output_dir}/all_urls.json', 'w', encoding='utf-8') as f:
            json.dump(all_links_data, f, indent=2)
        print(f'Saved all links to {self.output_dir}/all_urls.json')
        with open(f'{self.output_dir}/visited_urls.json', 'w', encoding='utf-8') as f:
            json.dump(visited_urls_data, f, indent=2)
        print(f'Saved visited URLs to {self.output_dir}/visited_urls.json')

    def save_failed_urls(self):
        """
        Saves list of failed URLs and their errors to a JSON file.
        Args:
            None
        Returns:
            None
        """
        data = {
            'company_name': self.company_name,
            'crawl_time': datetime.now().isoformat(),
            'failed_urls': list(self.failed_urls)
        }
        with open(f'{self.output_dir}/failed_urls.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f'Saved failed URLs to {self.output_dir}/failed_urls.json')


if __name__ == "__main__":
    web_urls = 'https://www.vishay.com'
    company_name = 'vishay'
    domain_limit = 'https://www.vishay.com' # None or specific domain, such as 'www.bmw.com/en-au'

    # Configure and start the crawler
    process = CrawlerProcess({
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'ERROR',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 1,
        'DOWNLOAD_TIMEOUT': 10
    })
    process.crawl(Spider, start_urls=[web_urls], company_name=company_name, domain_limit=domain_limit)
    process.start()
