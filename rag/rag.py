from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
import os
from typing import Dict, Any

class RAGSystem:
    def __init__(self):
        """
        Initialize RAG system with empty components.
        """
        self.openai_api_key = open('rag/openaikey.txt', 'r').read().strip()

        # Initialize embedding model
        self.embed_model = None
        # Load documents with progress bar
        self.documents = None
        # Create vector store index
        self.index = None
        # Create query engine with response synthesis
        self.query_engine = None

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
        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

    def query(self, question: str) -> Dict[str, Any]:
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
        response = self.query_engine.query(question)
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
        output = f"Answer: {result['answer']}\n\n"
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
        directory_path="./output/bmw-au"
    )
    
    print("Welcome to the BMW AU!")
    # Example query
    while True:
        question = input("Enter your question:\n")
        if question == "quit":
            break
        result = rag.query(question)
        print(rag.format_response(result))