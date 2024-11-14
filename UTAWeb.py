class UTAWeb:
    def __init__(self):
        self.rag_system = None
        self.crawler_process = None

    def crawl_web(self, web_urls: list[str], company_name: str, domain_limit: str):
        """
        Initialize and run web crawler on specified URLs.
        Args:
            web_urls (list[str]): List of starting URLs to crawl
            company_name (str): Name of company for organizing output
            domain_limit (str): Domain restriction for crawler (None for unrestricted)
        Returns:
            None: Crawled content is saved to disk in ./output/{company_name}
        """
        if not self.crawler_process:
            print("Crawler Initializing...")
            from crawler.crawler import Spider
            from scrapy.crawler import CrawlerProcess
            self.crawler_process = CrawlerProcess({
                'LOG_ENABLED': True,
                'LOG_LEVEL': 'ERROR',
                'ROBOTSTXT_OBEY': True,
                'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
                'DOWNLOAD_DELAY': 1,
                'DOWNLOAD_TIMEOUT': 10
            })
        self.crawler_process.crawl(Spider, start_urls=web_urls, company_name=company_name, domain_limit=domain_limit)
        self.crawler_process.start()

    def query_web(self, web_url: str, company_name: str):
        """
        Initialize RAG system and start interactive query loop.
        Args:
            web_url (str): URL of the website being queried (for display purposes)
            company_name (str): Name of company to load documents from
        Returns:
            None: Runs continuous query loop until 'quit' is entered
        """
        if not self.rag_system:
            print("RAG System Initializing...")
            from rag.rag import RAGSystem
            self.rag_system = RAGSystem()
            self.rag_system.initialize(
                directory_path=f"./output/{company_name}"
            )
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

    web_urls = 'https://www.vishay.com'
    company_name = 'vishay'
    domain_limit = 'https://www.vishay.com' # None or specific domain, such as 'www.bmw.com/en-au'

    # utaweb.crawl_web(web_urls=[web_urls], company_name=company_name, domain_limit=domain_limit)
    utaweb.query_web(web_url=web_urls, company_name=company_name)

