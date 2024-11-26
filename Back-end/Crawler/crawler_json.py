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

        def section_to_html(section, indent=0):
            html = []
            indent_str = '    ' * indent
            
            # Convert list to html
            def flush_list():
                if current_list:
                    html.append(f'{indent_str}<{current_list_type}>')
                    html.extend(f'{indent_str}    <li>{item}</li>' for item in current_list)
                    html.append(f'{indent_str}</{current_list_type}>')
                    current_list.clear()
            
            # Start section div
            html.append(f'{indent_str}<div class="section">')
            
            # Add heading
            if section['heading']:
                level, text = section['heading']['level'], section['heading']['text']
                html.append(f'{indent_str}    <{level}>{text}</{level}>')
            
            # Track list items for combining with links
            current_list = []
            current_list_type = None
            
            # Add content
            for item in section['content']:
                item_type = item['type']

                if item_type == 'paragraph':
                    flush_list()
                    html.append(f'{indent_str}<p>{item["text"]}</p>')

                elif item_type == 'image':
                    flush_list()
                    html.append(f'{indent_str}<img src="{item["src"]}" alt="{item.get("alt", "")}"/>')
                
                elif item_type == 'link':
                    # If we have a matching list item, combine them
                    if current_list and item['text'] in current_list:
                        idx = current_list.index(item['text'])
                        current_list[idx] = f'<a href="{item["href"]}">{item["text"]}</a>'
                    else:
                        flush_list()
                        html.append(f'{indent_str}<a href="{item["href"]}">{item["text"]}</a>')
            
                elif item_type == 'button':
                    text = item.get('text', None)
                    if text:
                        html.append(f'{indent_str}<button>{text}</button>')

                elif item_type == 'list':
                    current_list_type = item['list_type']
                    current_list.extend(item['items'])
                
            # Output any remaining list items
            flush_list()
            
            # Add subsections
            for subsection in section['subsections']:
                html.extend(section_to_html(subsection, indent + 1))
            
            # Close section div
            html.append(f'{indent_str}</div>')
            return html

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Initialize structure
        sections = []
        
        # Process elements
        for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'img', 'a', 'ul', 'ol', 'button']):
            # Skip empty elements and images that aren't inside links
            if not element.get_text(strip=True) and element.name not in ['img']:
                continue

            # Create content object
            if element.name.startswith('h'):
                content = {
                    'type': 'heading',
                    'level': element.name,
                    'text': element.get_text(strip=True)
                }
                new_section = create_section(element.name)
                new_section['heading'] = content
                
                if not sections:
                    sections.append(new_section)
                else:
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
            elif element.name == 'button':
                text = element.get_text(strip=True)
                if text:
                    content = {
                        'type': 'button',
                        'text': text
                    }

            if content:
                if not sections:
                    default_section = create_section()
                    sections.append(default_section)
                sections[-1]['content'].append(content)

        # Find root sections
        root_sections = []
        current_level = 0
        for section in sections:
            level = get_heading_level(section)
            if level <= current_level:
                root_sections.append(section)
                current_level = level

        # Create HTML output
        html_content = [
            '<!DOCTYPE html>',
            '<html>',
            '<head>',
            f'    <title>{soup.title.string if soup.title else "Scraped Page"}</title>',
            '    <meta charset="utf-8">',
            '    <style>',
            '        body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }',
            '        img { max-width: 100%; height: auto; }',
            '        h1, h2, h3 { color: #333; }',
            '        a { color: #0066cc; text-decoration: none; }',
            '        a:hover { text-decoration: underline; }',
            '        button { padding: 8px 16px; background-color: #0066cc; color: white; border: none; border-radius: 4px; cursor: pointer; }',
            '    </style>',
            '</head>',
            '<body>',
            f'    <p><strong>Source URL:</strong> <a href="{response.url}">{response.url}</a></p>',
            f'    <p><strong>Scraped on:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            '    <hr>'
        ]

        for section in root_sections:
            html_content.extend(section_to_html(section=section, indent=1))

        html_content.extend([
            '</body>',
            '</html>'
        ])

        filename = f"page_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        os.makedirs('scraped_data', exist_ok=True)
        
        with open(f'scraped_data/{filename}', 'w', encoding='utf-8') as f:
            f.write('\n'.join(html_content))

        print(f"Data saved to scraped_data/{filename}")

        yield {
            'url': response.url,
            'file': filename
        }

process = CrawlerProcess({
    'LOG_ENABLED': False
})
process.crawl(MySpider)
process.start()