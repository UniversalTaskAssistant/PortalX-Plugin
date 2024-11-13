from rag.rag import RAGSystem

class UTAWeb:
    def __init__(self, directory_path: str):
        self.openai_api_key = open('rag/openaikey.txt', 'r').read().strip()

        self.rag = RAGSystem(directory_path=directory_path,
                             openai_api_key=self.openai_api_key)

    def query_web(self, web_url: str):
        print(f'Welcome to the {web_url}!')
        while True:
            print("\n\n*************************\n")
            question = input("\nEnter your question:\n")
            if question == "quit":
                break
            result = self.rag.query(question)
            print(self.rag.format_response(result))


if __name__ == "__main__":
    web = UTAWeb(directory_path="./output/mankons")
    web.query_web("https://www.mankons.com")

