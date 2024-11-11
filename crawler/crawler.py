import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import os
from datetime import datetime
from urllib.parse import urlparse, quote

class Spider(scrapy.Spider):
    name = 'myspider'
    start_urls = ['https://www.bmw.com/en-au/home.html']
    
    def __init__(self, *args, **kwargs):
        super(Spider, self).__init__(*args, **kwargs)
        self.visited_urls = set()
        self.max_depth = 3
        self.domain_urls = {}
        self.max_urls_per_domain = 100
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = f'output/bmw'
        os.makedirs(self.output_dir, exist_ok=True)

    """
    ********************
    *** Main parsing ***
    ********************
    """
    def parse(self, response, depth=0):
        # Check if max urls per domain reached
        if depth >= self.max_depth:
            return
        domain = urlparse(response.url).netloc
        if domain not in self.domain_urls:
            self.domain_urls[domain] = 0
        if self.domain_urls[domain] >= self.max_urls_per_domain:
            return
        self.visited_urls.add(response.url)
        self.domain_urls[domain] += 1
        
        # Process and save current page
        print(f'Processing {response.url}')
        soup = self.clean_html(response)
        self.save_page_content(response.url, soup)
        
        # Extract and follow links
        links = []
        for link in response.css('a::attr(href)').getall():
            # Ignore page anchor
            if link.startswith('#'):
                continue
            absolute_url = response.urljoin(link)
            links.append(absolute_url)
            
            # Scrape the next page if it's valid
            if self.should_follow(absolute_url):
                yield scrapy.Request(
                    absolute_url,
                    callback=self.parse,
                    cb_kwargs={'depth': depth + 1},
                    errback=self.handle_error
                )
        self.save_links(response.url, links)

    """
    *********************
    *** HTML cleaning ***
    *********************
    """
    def clean_html(self, response):
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
    def should_follow(self, url):
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
        self.logger.error(f'Request failed: {failure.request.url}')

    """
    *******************
    *** File saving ***
    *******************
    """
    def filename_from_url(self, url):
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
            path = f'{path}?{quote(parsed_url.query, safe="")}'
            
        # Create full directory path and ensure it exists
        full_path = f'{domain_dir}/{path}'.replace('.html', '')
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        return full_path

    def save_page_content(self, url, soup):
        # Get the filename from the URL
        file_path = f'{self.filename_from_url(url)}.html'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f'Saved cleaned HTML to {file_path}')

    def save_links(self, source_url, links):
        data = {
            'source_url': source_url,
            'crawl_time': datetime.now().isoformat(),
            'links': links
        }
        # Get the filename from the URL
        file_path = f'{self.filename_from_url(source_url)}.json'
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f'Saved links to {file_path}')


# Configure and start the crawler
process = CrawlerProcess({
    'LOG_ENABLED': False,
    'LOG_LEVEL': 'INFO',
    'ROBOTSTXT_OBEY': True,
    'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
    'DOWNLOAD_DELAY': 1
})

process.crawl(Spider)
process.start()
