import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy import signals
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import json
import os
from os.path import join as pjoin
from datetime import datetime
from urllib.parse import urlparse, quote
import base64
from Crawler.html_parser import HTMLParser


class UTASpider(scrapy.Spider):
    """
    Scrapy spider for crawling websites and saving cleaned HTML content.
    Args:
        start_urls (list): Initial URLs to start crawling from
        company_name (str): Name of the company being crawled
        domain_limit (str): Optional domain restriction for crawling
    """
    name = 'UTASpider'

    def __init__(self, output_dir, start_urls=['https://www.bmw.com/en-au/index.html'], company_name='bmw', domain_limit=None, exclude_domains:list[str]=None,
                  *args, **kwargs):
        super(UTASpider, self).__init__(*args, **kwargs)
        self.html_parser = HTMLParser()

        # Website info
        self.name = company_name
        self.start_urls = start_urls 
        self.company_name = company_name 
        self.domain_limit = domain_limit
        self.exclude_domains = exclude_domains  # List of domains to exclude
        self.website_info = {}

        # Crawling parameters
        self.max_depth = 5
        self.max_urls_per_domain = 1000

        # Crawling state
        self.crawl_finished = False
        self.domain_urls = {}
        self.visited_urls = set()
        self.failed_urls = set()
        self.all_urls = set()

        # Output
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = pjoin(output_dir, self.company_name)
        os.makedirs(self.output_dir, exist_ok=True)


    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        """
        Connects the spider_closed signal to the spider_closed method
        """
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider
    
    """
    ********************
    *** Main parsing ***
    ********************
    """
    def parse(self, response, depth=0):
        if depth >= self.max_depth:
            return

        if not self.is_valid_url(response.url):
            return

        domain = urlparse(response.url).netloc
        if domain not in self.domain_urls:
            self.domain_urls[domain] = 0
        if self.domain_urls[domain] >= self.max_urls_per_domain:
            return

        self.visited_urls.add(response.url)
        self.domain_urls[domain] += 1

        try:
            print(f'\n*** Processing {response.url} ({len(self.visited_urls)}) ***')
            soup = self.html_parser.clean_html(response, self.all_urls)
            html_path = self.save_page_content(response.url, soup)

            # # Save all images on the page
            # image_urls = response.css('img::attr(src)').getall()
            # # for image_url in image_urls:
            # if len(image_urls) > 0:
            #     absolute_image_url = response.urljoin(image_urls[0])
            #     print(f'Found image URL: {absolute_image_url}')
            #     yield from self.save_image(absolute_image_url, response.url)

            # Follow links
            all_page_urls = response.css('a::attr(href)').getall()
            self.all_urls.update(all_page_urls)
            for link in all_page_urls:
                absolute_url = response.urljoin(link)
                if self.is_valid_url(absolute_url):
                    yield scrapy.Request(
                        absolute_url,
                        callback=self.parse,
                        cb_kwargs={'depth': depth + 1},
                        errback=self.handle_error
                    )

            self.save_website_info()
        except Exception as e:
            self.logger.error(f'!!!Error processing {response.url}: {e} !!!')
            self.failed_urls.add((response.url, str(e)))

    def spider_closed(self, spider):
        """
        Handler for spider_closed signal to perform cleanup tasks.
        Args:
            spider (UTASpider): The spider instance that was closed
        """
        self.crawl_finished = True
        self.save_website_info()  # Save final state
        print(f'\n!!! Crawling finished for {self.company_name} !!!\n')

    """
    *********************
    *** URL filtering ***
    *********************
    """
    def is_valid_url(self, url):
        """
        Determines if a URL should be crawled based on various criteria.
        Args:
            url (str): URL to evaluate
        Returns:
            bool: True if URL is valid, False otherwise
        """
        # Skip if it's just a page anchor
        if url.startswith('#'):
            return False
            
        # Skip if not a valid URL format
        if not url.startswith(('http://', 'https://')):
            return False
            
        parsed = urlparse(url)
        domain = parsed.netloc
        
        # Skip if already visited
        if url in self.visited_urls:
            return False
            
        # Skip if domain limit is set and URL doesn't match
        if self.domain_limit:
            parsed_url = urlparse(url)
            parsed_domain_limit = urlparse(self.domain_limit)
            
            # Compare domains and paths
            if parsed_url.netloc != parsed_domain_limit.netloc:
                return False
                
            # If domain limit includes a path, check if URL path starts with domain limit path
            if parsed_domain_limit.path:
                domain_limit_path = parsed_domain_limit.path.rstrip('/')
                url_path = parsed_url.path.rstrip('/')
                if not url_path.startswith(domain_limit_path):
                    return False
            
        # Skip if domain is in excluded domains
        if self.exclude_domains:
            for excluded in self.exclude_domains:
                if excluded in url:
                    return False
                    
        # Skip if max urls per domain reached
        if domain in self.domain_urls and self.domain_urls[domain] >= self.max_urls_per_domain:
            return False
            
        # Skip if file extension matches excluded types
        skip_extensions = ['.pdf', '.jpg', '.png', '.gif', '.zip']
        if any(url.lower().endswith(ext) for ext in skip_extensions):
            return False
            
        return True

    def handle_error(self, failure):
        """
        Handles failed requests during crawling.
        Args:
            failure (Failure): The failure object containing error details
        """
        failed_url = failure.request.url
        error_message = str(failure.value)
        self.failed_urls.add((failed_url, error_message))
        self.logger.error(f'Request failed: {failed_url}')

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
            path = 'root-index'
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
        """
        # Get the filename from the URL
        file_path = f'{self.filename_from_url(url)}.html'
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(str(soup))
        print(f'Saved cleaned HTML to {file_path}')
        return os.path.relpath(file_path, self.output_dir)

    def save_website_info(self):
        """
        Saves website information to a JSON file.
        """
        data = {
            'company_name': self.company_name,
            'start_urls': self.start_urls,
            'domain_limit': self.domain_limit,
            'domain_urls': self.domain_urls,
            'crawl_time': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'crawl_finished': self.crawl_finished,
            'visited_urls': list(self.visited_urls),
            'failed_urls': list(self.failed_urls)
        }
        with open(f'{self.output_dir}/website_info.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f'Saved website info to {self.output_dir}/website_info.json')


if __name__ == "__main__":
    web_urls = 'https://www.tum.de/en/'
    company_name = 'tum'
    domain_limit = 'https://www.tum.de/en/' # None or specific domain, such as 'www.bmw.com/en-au'

    # Configure and start the crawler
    process = CrawlerProcess({
        'LOG_ENABLED': True,
        'LOG_LEVEL': 'ERROR',
        'ROBOTSTXT_OBEY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'DOWNLOAD_DELAY': 1,
        'DOWNLOAD_TIMEOUT': 10
    })
    process.crawl(UTASpider, start_urls=[web_urls], company_name=company_name, domain_limit=domain_limit)
    process.start()
