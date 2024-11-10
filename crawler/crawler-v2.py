import scrapy
from scrapy.crawler import CrawlerProcess
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

class MySpider(scrapy.Spider):
    name = 'myspider'
    start_urls = ['https://www.bmw.com/en-au/home.html']

    def parse(self, response):
        # Create BeautifulSoup object from response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove all attributes except the allowed ones
        allowed_attrs = ['href', 'src', 'aria-label']
        for tag in soup.find_all():
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag[attr]
        
        # Remove redundant divs (divs with single child that's another div)
        self.remove_redundant_divs(soup)
        
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        # Save simplified HTML
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'output/simplified_{timestamp}.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify()))
        
        self.log(f'Simplified HTML saved to {output_path}')

    def remove_redundant_divs(self, soup):
        while True:
            redundant_found = False
            for div in soup.find_all('div'):
                # Check if div has exactly one child and it's another div
                children = list(div.children)
                children = [c for c in children if not isinstance(c, str) or c.strip()]
                
                if len(children) == 1 and children[0].name == 'div':
                    # Replace the parent div with its child's contents
                    div.replace_with(children[0])
                    redundant_found = True
                    break
            
            if not redundant_found:
                break

process = CrawlerProcess({
    'LOG_ENABLED': False
})
process.crawl(MySpider)
process.start()
