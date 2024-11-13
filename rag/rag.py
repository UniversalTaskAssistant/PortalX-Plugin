from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
import os
from typing import Dict, Any

class RAGSystem:
    def __init__(
        self, 
        directory_path: str,
        openai_api_key: str,
        embed_model: str = "BAAI/bge-small-en-v1.5",
        chunk_size: int = 1024,
        chunk_overlap: int = 200
    ):
        # Set OpenAI API key
        os.environ["OPENAI_API_KEY"] = openai_api_key
        
        # Initialize embedding model
        embed_model = HuggingFaceEmbedding(
            model_name=embed_model,
            embed_batch_size=100
        )
        
        # Configure settings with the new API
        Settings.llm = OpenAI(model="gpt-4o", temperature=0)
        Settings.embed_model = embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap
        
        # Load documents with progress bar
        self.documents = SimpleDirectoryReader(
            directory_path,
            recursive=True,
            exclude_hidden=True,
            filename_as_id=True
        ).load_data()
        
        # Create vector store index
        self.index = VectorStoreIndex.from_documents(
            self.documents,
            show_progress=True
        )
        
        # Create query engine with response synthesis
        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

    def query(self, question: str) -> Dict[str, Any]:
        """
        Query the document store with improved response formatting.
        
        Args:
            question: Query string
            
        Returns:
            Dictionary containing answer and source information
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
        Format the response in a readable way.
        """
        output = f"Answer: {result['answer']}\n\n"
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result['sources'], 1):
                output += f"\n{idx}. {source['file']}"
                # output += f"\n   Relevance Score: {source['score']}"
                # output += f"\n   Preview: {source['text_chunk']}\n"
        return output

# Example usage
if __name__ == "__main__":
    # Initialize system
    with open('rag/openaikey.txt', 'r') as file:
        openai_api_key = file.read().strip()
    rag = RAGSystem(
        directory_path="./output/bmw-au",
        openai_api_key=openai_api_key
    )
    
    print("Welcome to the BMW AU!")
    # Example query
    while True:
        question = input("Enter your question:\n")
        if question == "quit":
            break
        result = rag.query(question)
        print(rag.format_response(result))