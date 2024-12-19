from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.llama_pack import download_llama_pack
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
import os
import sys
import json
from typing import Dict, List, Any

class RAGSystem:
    def __init__(self):
        """
        Initialize RAG system with empty components.
        """
        if 'Backend' in sys.path[-1]:
            self.openai_api_key = open(os.path.join(sys.path[-1], 'RAG/openaikey.txt'), 'r').read().strip()
        else:
            self.openai_api_key = open('Backend/RAG/openaikey.txt', 'r').read().strip()

        self.current_directory_path = None  # Path to the currently loaded directory

        # Initialize embedding model
        self.embed_model = None
        # Load documents with progress bar
        self.documents = None
        # Create vector store index
        self.index = None
        # Create query engine with response synthesis
        self.query_engine = None
        # Create fuzzy citation query engine
        # self.fuzzy_engine_pack = None

        # self.storage_context = None

        # Create query engine with response synthesis and custom prompts
        self.system_prompt_answer_question = """You are a helpful AI website customer assistant that provides clear, structured answers based on website information.

        RESPONSE FORMAT REQUIREMENTS:
        
        1. Structure all responses in clean, semantic HTML
        2. Begin main answers with a short summary in a <div class="summary"> tag
        3. Use appropriate HTML elements:
           - <p> for paragraphs
           - <ul>/<li> for lists
           - <strong> for emphasis
           - <h3> for subsections
           - <a href="..."> for source links

        GUIDELINES:
        - Keep responses short, concise, and well-organized.
        - If none of the website information answer the question, say you will help redirect the question to customer service staff.
        - If the question is irrelevant to the website, just explain that you only answer website-relevant questions.
        - Always cite exact links using <a> tags when referencing specific information.
        - Interact with the user in a friendly and engaging manner.
        - Refer "The website" as "I", you are now representing the website.
        """

        # Conversation history with this user
        self.conversation_history = []

    def initialize(self, directory_path: str,
        embed_model_name: str = "BAAI/bge-small-en-v1.5",
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        load_from_disk: bool = True):
        """
        Initialize the RAG system components and load documents.
        Args:
            directory_path (str): Path to directory containing documents
            embed_model_name (str): Name of HuggingFace embedding model to use
            chunk_size (int): Size of text chunks for processing
            chunk_overlap (int): Number of overlapping tokens between chunks
            load_from_disk (bool): Whether to try loading saved index from disk
        """
        self.current_directory_path = directory_path

        # Initialize embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name=embed_model_name,
            embed_batch_size=100
        )
        # Configure settings with the new API
        os.environ["OPENAI_API_KEY"] = self.openai_api_key  
        Settings.llm = OpenAI(model="gpt-4o", system_prompt=self.system_prompt_answer_question)
        Settings.embed_model = self.embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

        # Try to load saved index if it exists
        if load_from_disk and os.path.exists(f"{directory_path}/embedding"):
            print("Loading saved index from disk...")
            from llama_index.core import StorageContext, load_index_from_storage
            self.storage_context = StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
            self.index = load_index_from_storage(self.storage_context)
        else:
            # Load documents and create new index
            print("Creating new index...")
            self.documents = SimpleDirectoryReader(
                directory_path,
                recursive=True,
                exclude_hidden=True,
                filename_as_id=True
            ).load_data()
            self.index = VectorStoreIndex.from_documents(
                self.documents,
                show_progress=True
            )
            # Save the index to disk
            self.index.storage_context.persist(persist_dir=f"{directory_path}/embedding")
            print("Index saved to disk.")

        # Create query engine with response synthesis
        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

        # FuzzyCitationEnginePack = download_llama_pack("FuzzyCitationEnginePack", "./fuzzy_pack")
        # self.fuzzy_engine_pack = FuzzyCitationEnginePack(self.query_engine, threshold=10)

        self.conversation_history = []

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Process a query against the document store.
        Args:
            question (str): User's question to be answered
        Returns:
            Dict[str, Any]: Dictionary containing:
                - answer (str): Generated response to the question
                - sources (list): List of dictionaries containing:
                    - file (str): Source filename
                    - score (float): Relevance score
                    - text_chunk (str): Preview of source text
        """
        Settings.llm.system_prompt = self.system_prompt_answer_question
        response = self.query_engine.query(question)
        # response = self.fuzzy_engine_pack.run(question)
        # print(f"Full answer: {str(response)}")
        self.conversation_history.append([question, str(response)])

        # TODO:
        # print(f"Metadata:\n{response.metadata.keys()}")
        # for response_sentence, node_chunk in response.metadata.keys():
        #     print("Response Sentence:\n", response_sentence)
        #     print("\nRelevant Node Chunk:\n", node_chunk)
        #     print("----------------")

        # for chunk_info in response.metadata.values():
        #     start_char_idx = chunk_info["start_char_idx"]
        #     end_char_idx = chunk_info["end_char_idx"]

        #     node = chunk_info["node"]
        #     node_start_char_idx = node.start_char_idx
        #     node_end_char_idx = node.end_char_idx

        #     # using the node start and end char idx, we can offset the citation chunk to locate the citation
        #     document_start_char_idx = start_char_idx + node_start_char_idx
        #     document_end_char_idx = document_start_char_idx + (end_char_idx - start_char_idx)
        #     documents = self.storage_context.docstore.get_all_documents()
        #     text = documents[0].text[document_start_char_idx:document_end_char_idx]

        #     print(text)
        #     print(node.metadata)
        #     print("----------------")

        # Format source documents
        sources = []
        for node in response.source_nodes:
            sources.append({
                'file': node.metadata.get('file_name', 'Unknown'),
                'score': round(node.score, 3) if node.score else None,
                'text_chunk': node.text[:200] + "..."  # Preview of the chunk
            })
        return {
            "answer": str(response),
            "sources": sources
        }
    
    def recommend_questions(self, recommended_question_number: int) -> List[str]:
        """
        Process a query against the document store.
        Args:
            question (str): User's question to be answered
        Returns:
            Dict[str, Any]: Dictionary containing:
                - answer (str): Generated response to the question
                - sources (list): List of dictionaries containing:
                    - file (str): Source filename
                    - score (float): Relevance score
                    - text_chunk (str): Preview of source text
        """

        system_prompt_recommend_question = f"""You are a helpful AI website customer assistant that recommends clear questions that the user might be interested, based on your conversation history with the user and website information.

        RESPONSE FORMAT REQUIREMENTS:
        1. Respond in JSON ONLY with format {{["your_question_1", "your_question_2", ...]}}.
        
        GUIDELINES:
        1. Keep questions short, concise, and well-organized.
        2. Refer "The website" as "I", you are now representing the website.

        DATA:
        1. Coversation history: {self.conversation_history}.
        """
        Settings.llm.system_prompt = system_prompt_recommend_question
        question = f"Please recommend {recommended_question_number} clear questions that the website user with the conversation might be interested."

        response = str(self.query_engine.query(question))
        # response = str(self.fuzzy_engine_pack.run(question))
        if response.startswith("```json"):
            response = str(response).removeprefix("```json").removesuffix("```").strip()

        return json.loads(response)

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = False) -> str:
        """
        Format the query response into a readable string.
        Args:
            result (Dict[str, Any]): Query result dictionary containing answer and sources
            show_sources (bool): Whether to include source information in output
        Returns:
            str: Formatted string containing answer and optional source information
        """
        # Remove code block markers and HTML tags from the answer
        output = result['answer']
        output = output.replace('```html', '').replace('```', '')
        
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result['sources'], 1):
                output += f"\n{idx}. {source['file']}"
                # output += f"\n   Relevance Score: {source['score']}"
                # output += f"\n   Preview: {source['text_chunk']}\n"
        return output


if __name__ == "__main__":
    rag = RAGSystem()
    rag.initialize(
        directory_path="./Output/websites/tum"
    )
    
    print("Welcome!")
    # Example query
    while True:
        question = input("Enter your question:\n")
        if question == "quit":
            break
        result = rag.query(question)
        print(rag.format_response(result))