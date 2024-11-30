from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings, BasePromptTemplate
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.core import get_response_synthesizer
from llama_index.core.query_engine import RetrieverQueryEngine
from typing import Dict, Any, List
from llama_index.core.prompts import PromptTemplate
import Stemmer
import os
from dotenv import load_dotenv
from langsmith.run_helpers import traceable


class RAGSystem:
    def __init__(self):
        """
        Initialize RAG system with empty components.
        """
        # Determine the path to the 'openaikey.txt' file


        # Load environment variables from .env file
        load_dotenv()

        # Load the OpenAI API key
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

        # Initialize other attributes
        self.current_directory_path = None  # Path to the currently loaded directory
        self.embed_model = None            # Initialize embedding model
        self.documents = None              # Placeholder for documents
        self.index = None                  # Vector store index
        self.query_engine = None           # Query engine with response synthesis
        self.custom_prompt = self.load_custom_prompt()

    def load_custom_prompt(self) -> str:
        """
        Load the custom prompt from the prompts/custom_prompt.txt file.
        Returns:
            str: The custom prompt as a string.
        """
        prompt_file_path = os.path.join(os.path.dirname(__file__), 'prompts', 'custom_prompt.txt')

        if os.path.exists(prompt_file_path):
            with open(prompt_file_path, 'r') as prompt_file:
                return prompt_file.read()
        else:
            raise FileNotFoundError(f"Custom prompt file not found at {prompt_file_path}. Please ensure it exists.")

    def initialize(self, directory_path: str,
                   embed_model_name: str = "hkunlp/instructor-xl",
                   chunk_size: int = 1024,
                   chunk_overlap: int = 200,
                   load_from_disk: bool = True):
        """
        Initialize the RAG system components and load documents.
        """
        self.current_directory_path = directory_path

        # Initialize embedding model
        self.embed_model = HuggingFaceEmbedding(
            model_name=embed_model_name,
            embed_batch_size=100
        )

        # Configure settings with the new API
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        Settings.llm = OpenAI(model="gpt-4", temperature=0)
        Settings.embed_model = self.embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

        self._load_index(directory_path, load_from_disk)

        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True,
            custom_prompt=self.custom_prompt
        )

    def _load_index(self, directory_path, load_from_disk):
        if load_from_disk and os.path.exists(f"{directory_path}/embedding"):
            print("Loading saved index from disk...")
            from llama_index.core import StorageContext, load_index_from_storage
            storage_context = StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
            self.index = load_index_from_storage(storage_context)
        else:
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
            self.index.storage_context.persist(persist_dir=f"{directory_path}/embedding")
            print("Index saved to disk.")

    @traceable(run_type="chain")
    def retrieve_documents(self, question: str, top_k: int = 3) -> list:
        """
        Retrieve relevant documents and compress/filter them.
        """
        if not self.index:
            raise ValueError("Index has not been initialized.")

        # Retrieve documents from the index
        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)
        retrieved_docs = response.source_nodes

        return retrieved_docs

    @traceable(run_type="chain")
    def generate_custom_response(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Generate a response by manually controlling the RAG pipeline.
        """
        # Step 1: Retrieve documents
        retrieved_docs = self.retrieve_documents(question, top_k=top_k)

        #TODO Step 2: Compress and filter documents
        llm = OpenAI(model="gpt-4", temperature=0)
        compressed_docs = self.compress_and_filter_documents(retrieved_docs, question, llm)

        # Step 3: Construct context
        context = "\n".join([doc.text for doc in compressed_docs])

        # Step 4: Use custom prompt to generate response
        llm = OpenAI(model="gpt-4", temperature=0)
        prompt = PromptTemplate(self.custom_prompt)
        answer = llm.predict(prompt, query=question, retrieved_documents=context)

        return {
            "answer": answer,
            "sources": [
                {
                    "file": doc.metadata.get('file_name', 'Unknown'),
                    "score": round(doc.score, 3) if doc.score else None,
                    "text_chunk": doc.text[:200] + "..."
                } for doc in compressed_docs
            ]
        }

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str, llm) -> List[NodeWithScore]:
        """
        Compress and filter documents using the language model.
        """
        # Initialize an empty list to store the filtered and summarized documents
        filtered_docs = []

        # Loop through each NodeWithScore and process it individually
        for node_with_score in docs:
            # Extract the TextNode and its text content
            text_node = node_with_score.node
            doc_text = text_node.text
            metadata = text_node.metadata

            # Construct the compression prompt
            prompt = (
                f"The following is a document retrieved based on a generalized version of the original question:\n\n"
                f"Original Question: {question}\n\n"
                "Generalized Question:\n"
                "Adjust the question to a broader scope to ensure the document is evaluated for any potentially useful information:\n"
                "Generalized Question: {generalized_question}\n\n"
                f"Document Text:\n{doc_text}\n\n"
                "Task:\n"
                "1. Determine if the document contains information broadly related to the generalized question.\n"
                "2. If the document is irrelevant to the generalized question, return an empty response.\n"
                "3. If the document is relevant to the generalized question, summarize the text while retaining as much useful information as possible for answering the original question.\n\n"
                "Output:\n"
                "Summarized Text (or empty if not relevant):"
            )

            prompt = PromptTemplate(prompt)

            answer = llm.predict(prompt, query=question, doc_text=doc_text)
            # Generate a response using the LLM
            summarized_text = answer.strip() if answer else ""

            # Skip documents with empty responses
            if not summarized_text:
                continue

            # Create a new TextNode with the summarized text
            summarized_node = TextNode(
                id_=text_node.id_,
                text=summarized_text,
                metadata=metadata  # Retain metadata
            )

            # Wrap the new TextNode in a NodeWithScore
            filtered_node_with_score = NodeWithScore(
                node=summarized_node,
                score=node_with_score.score  # Retain the score from the original NodeWithScore
            )

            # Add the filtered NodeWithScore to the list
            filtered_docs.append(filtered_node_with_score)

        return filtered_docs

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = True) -> str:
        """
        Format the query response into a readable string.
        """
        output = f"Answer: {result['answer']}\n\n"
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result['sources'], 1):
                output += f"\n{idx}. {source['file']}"
        return output

if __name__ == "__main__":
    rag = RAGSystem()
    relative_directory_path = "../Output/websites/tum"
    absolute_directory_path = os.path.abspath(relative_directory_path)
    rag.initialize(directory_path=absolute_directory_path)
    print("Welcome!")

    while True:
        question = input("Enter your question:\n")
        if question == "quit":
            break
        response = rag.generate_custom_response(question)
        print("Answer:", response["answer"])
        print("Sources:", response["sources"])
