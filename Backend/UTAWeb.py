import tldextract
import os
from os.path import join as pjoin
from Crawler.crawler import UTASpider
from scrapy.crawler import CrawlerProcess


class UTAWeb:
    _rag_systems = {}  # Dictionary to store RAG systems by company_name in memory

    def __init__(self, initializing=False, data_dir=None, recommended_question_number=3):
        self.crawler_process = None  # Temporary crawler process worker without storing in memory
        self.data_dir = data_dir if data_dir is not None else "./Backend/Output/websites"
        if initializing:
            self.initialize_crawler()
            self.initialize_rag()

        self.recommended_question_number = recommended_question_number

    """
    **********************
    *** Initialization ***
    **********************
    """
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
        # Initialize RAG System for specific company if not exists
        company_name = directory_path.replace('\\', '/').split('/')[-1] if directory_path else None
        if company_name not in self._rag_systems:
            print(f"Initializing RAG System for {company_name}...")
            from RAG.rag_v2 import RAGSystem
            self._rag_systems[company_name] = RAGSystem()
            if directory_path:
                self._rag_systems[company_name].initialize(directory_path=directory_path)
        return self._rag_systems[company_name]

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

    def crawl_web(self, web_url: str, company_name: str=None, domain_limit: str=None, exclude_domains: list[str]=None):
        """
        Initialize and run web crawler on specified URLs.
        Args:
            web_urls (list[str]): List of starting URLs to crawl
            company_name (str): Name of company for organizing output
            domain_limit (str): Domain restriction for crawler (None for unrestricted)
        Returns:
            str: 'Exist' if company directory exists and contains files, 'Success' if crawling is successful
        """
        company_name = self.get_company_name_from_url(web_url) if company_name is None else company_name
        company_dir = pjoin(self.data_dir, company_name)
        
        # Check if company directory exists and contains files
        if os.path.exists(company_dir) and os.listdir(company_dir):
            print(f"\n!!! Website data for {web_url} already exists in {company_dir} !!!\n")
            return 'Exist'
        # Initialize crawler and start crawling
        else:   
            self.initialize_crawler()
            self.crawler_process.crawl(UTASpider, output_dir=self.data_dir, start_urls=[web_url], company_name=company_name, domain_limit=domain_limit, exclude_domains=exclude_domains)
            self.crawler_process.start()
            return 'Success'

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
        rag_system = self.initialize_rag(directory_path=pjoin(self.data_dir, company_name))
        result = rag_system.query(query)
        formatted_response = rag_system.format_response(result)
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
        rag_system = self.initialize_rag(directory_path=pjoin(self.data_dir, company_name))
        print(f'Welcome to the {web_url}!')

        recommended_questions = rag_system.recommend_questions(self.recommended_question_number)
        print("----------")
        print(f"Recommended initial questions: {recommended_questions}")
        print("----------")

        while True:
            print("\n\n*************************\n")
            question = input("\nEnter your question:\n")
            if question == "quit":
                break
            result = rag_system.answer_question(question)
            print(result['sources'])
            print(rag_system.format_response(result))
            recommended_questions = rag_system.recommend_questions(self.recommended_question_number)
            print("----------")
            print(f"Recommended conversational questions: {recommended_questions}")
            print("----------")


if __name__ == "__main__":
    utaweb = UTAWeb()

    web_url = 'https://www.tum.de/en/'
    company_name = 'tum'
    domain_limit = 'https://www.tum.de/en/' # None or specific domain, such as 'www.bmw.com/en-au'

    # web_url = 'https://www.signavio.com/'
    # company_name = 'signavio'
    # domain_limit = 'https://www.signavio.com/' # None or specific domain, such as 'www.bmw.com/en-au'
    # exclude_domains = ['www.signavio.com/de', 'www.signavio.com/es', 'www.signavio.com/fr', 'www.signavio.com/it', 'www.signavio.com/ja', 'www.signavio.com/ko', 'www.signavio.com/pt-br']

    # utaweb.crawl_web(web_url=web_url, company_name=company_name, domain_limit=domain_limit, exclude_domains=None)
    # utaweb.query_web(query="Explain the MINT study program?", web_url=web_url)
    # utaweb.query_web(query="How many Nobel awardees graduated from TUM?", web_url=web_url)
    # utaweb.query_web(query="Can you explain to me who is Donald Trump?", web_url=web_url)
    utaweb.query_web_test(web_url=web_url, company_name=company_name)

