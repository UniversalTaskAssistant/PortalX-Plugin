from bs4 import BeautifulSoup


class HTMLParser:
    def __init__(self):
        pass

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
            BeautifulSoup: Cleaned HTML soup object
        """
        soup = BeautifulSoup(response.text, 'html.parser')

        # Clean head
        self.clean_head(soup, response.url)
        # Clean elements
        self.clean_elements(soup, existing_urls)
        # Remove redundant divs
        self.remove_redundant_divs(soup)
        
        return BeautifulSoup(soup.prettify(formatter='html5'), 'html.parser')

    def clean_head(self, soup, page_url):
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
        # Add source URL and title stamp at the beginning of body
        body = soup.find('body')
        if body:
            title_text = soup.find('title').string if soup.find('title') else "No title"
            stamp_html = f'''
            <div>
                <h1>Source URL: <a href="{page_url}">{page_url}</a>
                <br>Title: {title_text}</h1>
                <hr>
            </div>
            '''
            body.insert(0, BeautifulSoup(stamp_html, 'html.parser'))

    def clean_elements(self, soup, existing_urls=None):
        """
        Cleans and simplifies HTML content by removing unnecessary elements and attributes.
        Args:
            soup (BeautifulSoup): The HTML soup object to clean
            existing_urls (set): Set of all URLs that have been discovered
        Returns:
            None (modifies soup object in place)
        """
        # Clean elements
        for tag in soup.find_all(['script', 'style', 'source']):
            tag.decompose()

        # Remove <a> tags that point to any discovered URLs
        if existing_urls and len(existing_urls) > 0:
            for a_tag in soup.find_all('a'):
                href = a_tag.get('href')
                if href and href in existing_urls:
                    a_tag.decompose()

        # Remove unused attributes
        allowed_attrs = ['href', 'src', 'aria-label', 'type']
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

    @staticmethod
    def remove_redundant_divs(soup):
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