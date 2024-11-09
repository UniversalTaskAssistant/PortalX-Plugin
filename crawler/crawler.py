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
        from bs4 import BeautifulSoup
        import json
        import os
        from datetime import datetime

        def create_section(level='h1'):
            return {
                'heading': None,
                'content': [],
                'subsections': []
            }

        def get_heading_level(section):
            if section and section['heading'] and section['heading']['level']:
                return int(section['heading']['level'][1])
            return 0

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize structure
        sections = []
        
        # Process elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'img', 'a', 'ul', 'ol']):
            if not element.get_text(strip=True) and element.name not in ['img']:
                continue

            # Skip images that aren't inside links
            if element.name == 'img' and not element.find_parent('a'):
                continue

            # Create content object
            if element.name.startswith('h'):
                content = {
                    'type': 'heading',
                    'level': element.name,
                    'text': element.get_text(strip=True)
                }
                # Start new section
                new_section = create_section(element.name)
                new_section['heading'] = content
                
                if not sections:
                    sections.append(new_section)
                else:
                    # Find appropriate parent section
                    current_level = int(element.name[1])
                    while sections and get_heading_level(sections[-1]) >= current_level:
                        sections.pop()
                    
                    if not sections:
                        sections.append(new_section)
                    else:
                        sections[-1]['subsections'].append(new_section)
                        sections.append(new_section)
                continue

            # Handle other content types
            content = None
            if element.name == 'p':
                text = element.get_text(strip=True)
                if text:
                    content = {
                        'type': 'paragraph',
                        'text': text
                    }
            elif element.name == 'img' and element.find_parent('a'):
                content = {
                    'type': 'image',
                    'src': element.get('src'),
                    'alt': element.get('alt')
                }
            elif element.name == 'a':
                text = element.get_text(strip=True)
                href = element.get('href')
                if text or href:
                    content = {
                        'type': 'link',
                        'text': text,
                        'href': href
                    }
            elif element.name in ['ul', 'ol']:
                items = [li.get_text(strip=True) for li in element.find_all('li')]
                if items:
                    content = {
                        'type': 'list',
                        'list_type': element.name,
                        'items': items
                    }

            # Add content to current section
            if content:
                if not sections:
                    default_section = create_section()
                    sections.append(default_section)
                sections[-1]['content'].append(content)

        # Find root sections (only keep the top-level ones)
        root_sections = []
        current_level = 0
        for section in sections:
            level = get_heading_level(section)
            if level <= current_level:
                root_sections.append(section)
                current_level = level

        # Save to JSON
        data = {
            'url': response.url,
            'timestamp': datetime.now().isoformat(),
            'title': soup.title.string if soup.title else None,
            'sections': root_sections
        }

        filename = f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('scraped_data', exist_ok=True)
        
        with open(f'scraped_data/{filename}', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        yield data

process = CrawlerProcess()
process.crawl(MySpider)
process.start()
