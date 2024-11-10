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
        
        # Clean head section
        head = soup.find('head')
        if head:
            # Remove all elements from head except title
            for tag in head.find_all():
                if tag.name != 'title':
                    tag.decompose()
        
        # Remove script and style tags
        for tag in soup.find_all(['script', 'style']):
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
        
        # Remove all attributes except the allowed ones
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
        
        # Remove redundant divs (divs with single child that's another div)
        self.remove_redundant_divs(soup)
        
        # Create output directory if it doesn't exist
        os.makedirs('output', exist_ok=True)
        
        # Save compressed HTML
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = f'output/simplified_{timestamp}.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(str(soup.prettify(formatter="minimal")))
        
        self.log(f'Simplified HTML saved to {output_path}')

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

process = CrawlerProcess({
    'LOG_ENABLED': False
})
process.crawl(MySpider)
process.start()
