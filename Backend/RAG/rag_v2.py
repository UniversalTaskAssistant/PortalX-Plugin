from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.core.query_engine import CitationQueryEngine
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from bs4 import BeautifulSoup
import os
import re
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
            self.openai_api_key = open('RAG/openaikey.txt', 'r').read().strip()

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
        self.fuzzy_engine_pack = None

        # self.storage_context = None

        # Create query engine with response synthesis and custom prompts
        self.system_prompt_answer_question = ""

        self.system_prompt_recommend_question = ""

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
            storage_context = StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
            self.index = load_index_from_storage(storage_context)
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
        # self.query_engine = self.index.as_query_engine(
        #     response_mode="tree_summarize",
        #     similarity_top_k=3,
        #     streaming=True
        # )

        self.query_engine = CitationQueryEngine.from_args(
            self.index,
            similarity_top_k=3,
            # Here we can control how granular citation sources are, the default is 512
            citation_chunk_size=512,
        )

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

        question = f"""You are a helpful AI website customer assistant that provides clear and structured answer for the question, based on website information and your conversation history with the user.

        QUESTION: {question}\n

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

        DATA:
        1. Coversation history: {self.conversation_history}.
        """
        # Settings.llm.system_prompt = self.system_prompt_answer_question
        response = self.query_engine.query(question)
        self.conversation_history.append([question, str(response)])

        # Format source documents
        references = []
        for node in response.source_nodes:
            references.append({
                'file': node.metadata.get('file_name', 'Unknown'),
                # 'score': round(node.score, 3) if node.score else None,
                'text_chunk': node.text[:200] + "..."  # Preview of the chunk
            })
        
        answer_with_citations = str(response)
        # print(f"###############\n{answer_with_citations}\n###############\n")
        # print(f"###############\n{references}\n###############\n")
        return {
            "references": references,
            "answer_with_citations": answer_with_citations
        }
    

    def recommend_questions(self, recommended_question_number: int=3) -> str:
        """
        Recommend initial and conversational questions.
        Args:
            recommended_question_number (int): number of recommended questions
        Returns:
            str: all questions in html
        """

        self.system_prompt_recommend_question = f"""You are a helpful AI website customer assistant that recommends clear questions that the user might be interested, based on your conversation history with the user and website information.

        RESPONSE FORMAT REQUIREMENTS:
        1. Merge all questions together in a HTML ``<div class="recommendation">`` tag.
        2. Use HTML tag ``<span class="recommendation-item">`` for each question.
        
        GUIDELINES:
        1. Keep questions short, concise, and well-organized.
        2. Refer "The website" as "I", you are now representing the website.

        DATA:
        1. Coversation history: {self.conversation_history}.
        """
        Settings.llm.system_prompt = self.system_prompt_recommend_question
        question = f"Please recommend {str(recommended_question_number)} clear questions that the website user with the conversation might be interested."

        response = str(self.query_engine.query(question))
        if response.startswith("```html"):
            response = str(response).removeprefix("```html").removesuffix("```").strip()

        return response

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = True) -> str:
        """
        Format the query response into a readable string.
        Args:
            result (Dict[str, Any]): Query result dictionary containing answer and sources
            show_sources (bool): Whether to include source information in output
        Returns:
            str: Formatted string containing answer and optional source information
        """
        # Remove code block markers and HTML tags from the answer
        output = result['answer_with_citations']
        output = output.replace('```html', '').replace('```', '')
        
        if show_sources:
            references_content = '<div class="references">\n'
            references_content += "<p>References:</p>\n"
            references_content += '<ul class="reference-list">\n'
            for idx, reference in enumerate(result['references'], 1):
                references_content += f'<li class="reference-item">\n'
                references_content += f'<p>{idx}</p>\n'
                references_content += f'<p>{reference["file"]}</p>\n'
                # references_content += f'<p class="relevance-score">Relevance Score: {reference["score"]}</p>\n'
                references_content += f'<p class="preview">{reference["text_chunk"]}</p>\n'
                references_content += '</li>\n'
            references_content += '</ul>\n'
            references_content += '</div>\n'
            output += references_content
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