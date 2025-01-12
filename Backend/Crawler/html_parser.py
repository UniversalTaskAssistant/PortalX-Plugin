from bs4 import BeautifulSoup

class HTMLParser:
    def __init__(self):
        # Record header and footer to remove redundancies
        self.header = None
        self.footer = None

    """
    *********************
    *** HTML cleaning ***
    *********************
    """
    def clean_html(self, response, existing_urls=None):
        """
        Cleans and simplifies HTML content by removing unnecessary elements and attributes.
        Args:
            response (scrapy.Response): The response object containing the webpage
            existing_urls (set): Set of all URLs that have been discovered
        Returns:
            str: Markdown content generated from cleaned HTML
        """
        soup = BeautifulSoup(response.text, 'html.parser')

        # Clean head
        self.clean_head(soup)
        # Clean elements
        self.clean_elements(soup)

        # Remove existing link elements
        self.remove_existing_link_elements(soup, existing_urls)
        # Remove empty elements
        self.remove_empty_elements(soup)
        # Remove redundant divs
        self.remove_redundant_divs(soup)

        # Add title and generate markdown content
        markdown_content = self.generate_markdown(soup, response.url)
        return markdown_content

    def clean_head(self, soup):
        """
        Cleans and simplifies HTML content by removing unnecessary elements and attributes.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
        Returns:
            None (modifies soup object in place)
        """
        # Clean head section
        head = soup.find('head')
        if head:
            # Remove all elements from head except title
            for tag in head.find_all():
                if tag.name != 'title':
                    tag.decompose()

    def clean_elements(self, soup):
        """
        Cleans and simplifies HTML content by removing unnecessary elements and attributes.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
        Returns:
            None (modifies soup object in place)
        """
        # Remove script, style, and source tags
        for tag in soup.find_all(['script', 'style', 'source', 'svg']):
            tag.decompose()

        # Remove unused attributes
        allowed_attrs = ['href', 'src', 'aria-label', 'type']
        for tag in soup.find_all():
            attrs = dict(tag.attrs)
            for attr in attrs:
                if attr not in allowed_attrs:
                    del tag[attr]

    def remove_existing_link_elements(self, soup, existing_urls):
        """
        Removes <a> tags that point to discovered URLs.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
            existing_urls (set): Set of all URLs that have been discovered
        Returns:
            None (modifies soup object in place)
        """
        # Remove <a> tags that point to discovered URLs
        if existing_urls and len(existing_urls) > 0:
            for a_tag in soup.find_all('a'):
                href = a_tag.get('href')
                if href and href in existing_urls:
                    a_tag.decompose()

    def remove_empty_elements(self, soup):
        """
        Removes empty elements from HTML.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
        Returns:
            None (modifies soup object in place)
        """
        # Tags that should be kept even when empty
        preserve_tags = {'hr', 'br', 'img', 'input', 'meta', 'link', 'textarea'}

        # Recursively remove empty elements
        while True:
            removed = False
            for tag in soup.find_all():
                # Skip if tag should be preserved
                if tag.name in preserve_tags:
                    continue
                # Skip if tag has attributes
                if tag.attrs:
                    continue
                # Get content (excluding whitespace)
                content = ''.join(str(child) for child in tag.contents).strip()
                # Remove if empty (no content and no attributes)
                if not content:
                    tag.decompose()
                    removed = True
                    break
            if not removed:
                break

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

    def generate_markdown(self, soup, page_url):
        """
        Converts the cleaned HTML content into structured Markdown format.
        Args:
            soup (BeautifulSoup): The cleaned HTML soup object
            page_url (str): The URL of the page
        Returns:
            str: Markdown representation of the HTML content
        """
        title = soup.find('title').string if soup.find('title') else "Untitled Page"
        markdown = f"# {title}\n\n"  # Title as Markdown header
        markdown += f"Source: [{page_url}]({page_url})\n\n"

        for tag in soup.find_all(['h1', 'h2', 'h3', 'p', 'a', 'ul', 'ol', 'li']):
            if tag.name == 'h1':
                markdown += f"# {tag.get_text(strip=True)}\n\n"
            elif tag.name == 'h2':
                markdown += f"## {tag.get_text(strip=True)}\n\n"
            elif tag.name == 'h3':
                markdown += f"### {tag.get_text(strip=True)}\n\n"
            elif tag.name == 'p':
                markdown += f"{tag.get_text(strip=True)}\n\n"
            elif tag.name == 'a':
                link_text = tag.get_text(strip=True)
                href = tag.get('href', '#')
                markdown += f"[{link_text}]({href})\n\n"
            elif tag.name in ['ul', 'ol']:
                for li in tag.find_all('li'):
                    markdown += f"- {li.get_text(strip=True)}\n"
                markdown += "\n"

        return markdown
