import tldextract
from os.path import join as pjoin
from Crawler.crawler import Spider
from scrapy.crawler import CrawlerProcess

class UTAWeb:
    def __init__(self, initializing=False, data_dir=None):
        self.rag_system = None
        self.crawler_process = None

        self.data_dir = data_dir if data_dir is not None else "./Output/websites"
        if initializing:
            self.initialize()

    """
    **********************
    *** Initialization ***
    **********************
    """
    def initialize(self):
        # Initialize Crawler
        self.initialize_crawler()
        # Initialize RAG System
        self.initialize_rag(directory_path=None)

    def initialize_crawler(self):
        # Initialize Crawler    
        if not self.crawler_process:
            print("Crawler Initializing...")
            self.crawler_process = CrawlerProcess({
                'LOG_ENABLED': True,
                'LOG_LEVEL': 'ERROR',
                'ROBOTSTXT_OBEY': True,
                'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
                'DOWNLOAD_DELAY': 1,
                'DOWNLOAD_TIMEOUT': 10
            })

    def initialize_rag(self, directory_path: str=None):
        # Initialize RAG System
        if not self.rag_system:
            print("RAG System Initializing...")
            from RAG.rag import RAGSystem
            self.rag_system = RAGSystem()
        # Initialize RAG System if directory path is specified and different from the current directory path
        if directory_path and self.rag_system.current_directory_path != directory_path:
            self.rag_system.initialize(directory_path=directory_path)

    """
    **********************
    *** Main Functions ***
    **********************
    """
    @staticmethod
    def get_company_name_from_url(web_url: str):
        """
        Extract company name from URL.
        Args:
            web_url (str): URL of the website
        Returns:
            str: Company name
        """
        extracted = tldextract.extract(web_url)
        if extracted.subdomain not in ['www', '']:
            company_name = f"{extracted.subdomain}.{extracted.domain}"
        else:   
            company_name = extracted.domain
        return company_name

    def crawl_web(self, web_url: str, company_name: str=None, domain_limit: str=None):
        """
        Initialize and run web crawler on specified URLs.
        Args:
            web_urls (list[str]): List of starting URLs to crawl
            company_name (str): Name of company for organizing output
            domain_limit (str): Domain restriction for crawler (None for unrestricted)
        Returns:
            None: Crawled content is saved to disk in ./Output/websites/{company_name}
        """
        company_name = self.get_company_name_from_url(web_url) if company_name is None else company_name
        self.initialize_crawler()
        self.crawler_process.crawl(Spider, output_dir=self.data_dir, start_urls=[web_url], company_name=company_name, domain_limit=domain_limit)
        self.crawler_process.start()

    def query_web(self, query: str, web_url: str, company_name=None):
        """
        Query RAG system with a question and return formatted response.
        Args:
            query (str): Question to query RAG system with
            web_url (str): URL of the website being queried (for display purposes)
            company_name (str): Name of company to load documents from
        Returns:
            str: Formatted response from RAG system
        """
        company_name = self.get_company_name_from_url(web_url) if company_name is None else company_name
        self.initialize_rag(directory_path=pjoin(self.data_dir, company_name))
        result = self.rag_system.query(query)
        formatted_response = self.rag_system.format_response(result)
        print(formatted_response)
        return formatted_response

    def query_web_test(self, web_url: str, company_name=None):
        """
        Initialize RAG system and start interactive query loop.
        Args:
            web_url (str): URL of the website being queried (for display purposes)
            company_name (str): Name of company to load documents from
        Returns:
            None: Runs continuous query loop until 'quit' is entered
        """
        company_name = self.get_company_name_from_url(web_url) if company_name is None else company_name
        self.initialize_rag(directory_path=pjoin(self.data_dir, company_name))
        print(f'Welcome to the {web_url}!')
        while True:
            print("\n\n*************************\n")
            question = input("\nEnter your question:\n")
            if question == "quit":
                break
            result = self.rag_system.query(question)
            print(self.rag_system.format_response(result))


if __name__ == "__main__":
    utaweb = UTAWeb()

    web_url = 'https://www.tum.de/en/'
    company_name = 'tum'
    domain_limit = 'https://www.tum.de/en/' # None or specific domain, such as 'www.bmw.com/en-au'

    utaweb.crawl_web(web_url=web_url, company_name=None, domain_limit=None)
    # utaweb.query_web(query="What is the name of the university?", web_url=web_url)
    # utaweb.query_web_test(web_url=web_url, company_name=company_name)

