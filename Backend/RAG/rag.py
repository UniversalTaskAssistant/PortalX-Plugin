import asyncio

from llama_index.core import StorageContext, VectorStoreIndex, SimpleDirectoryReader, Settings, load_index_from_storage
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from typing import Dict, Any, List
import os
from dotenv import load_dotenv
from langsmith.run_helpers import traceable

from Backend.RAG.prompts import COMPRESS_AND_FILTER_PROMPT, ANSWER_PROMPT


class RAGSystem:
    def __init__(self):
        """
        Initialize RAG system with empty components.
        """

        load_dotenv()
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

    def initialize(self, directory_path: str,
                   embed_model_name: str = "hkunlp/instructor-xl",
                   chunk_size: int = 1024,
                   chunk_overlap: int = 200,
                   load_from_disk: bool = True):
        """
        Initialize the RAG system components and load documents.
        """
        self.current_directory_path = directory_path

        os.makedirs(directory_path, exist_ok=True)

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
        )

    def _load_index(self, directory_path, load_from_disk):
        if load_from_disk and os.path.exists(f"{directory_path}/embedding"):
            print("Loading saved index from disk...")
            storage_context = StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
            self.index = load_index_from_storage(storage_context)
        else:
            print("Creating new index incrementally...")
            self.documents = SimpleDirectoryReader(
                directory_path,
                recursive=True,
                exclude_hidden=True,
                filename_as_id=True
            ).load_data()

            storage_context = StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")

            async def process_and_store_document(document):
                print(f"Embedding document: {document.doc_id}")
                doc_index = VectorStoreIndex.from_documents([document])
                doc_index.storage_context.persist(persist_dir=storage_context.persist_dir)
                print(f"Document {document.doc_id} saved successfully.")

            async def process_all_documents():
                tasks = [
                    process_and_store_document(document) for document in self.documents
                ]
                await asyncio.gather(*tasks)

            asyncio.run(process_all_documents())
            print("All documents have been embedded and saved incrementally.")



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
    async def generate_custom_response(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        Generate a response by manually controlling the RAG pipeline.
        """
        # Step 1: Retrieve documents
        retrieved_docs = self.retrieve_documents(question, top_k=top_k)

        #Step 2: Compress and filter documents
        llm = OpenAI(model="gpt-4", temperature=0)
        compressed_docs = await self.compress_and_filter_documents(retrieved_docs, question, llm)

        # Step 3: Construct context
        context = "\n".join([doc.text for doc in compressed_docs])

        # Step 4: Use custom prompt to generate response
        llm = OpenAI(model="gpt-4", temperature=0)
        answer = llm.predict(ANSWER_PROMPT, question=question, context=context)

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
    async def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str, llm) -> List[NodeWithScore]:
        """
        Compress and filter documents using the language model asynchronously.
        """

        async def process_document(node_with_score):
            text_node = node_with_score.node
            doc_text = text_node.text
            metadata = text_node.metadata


            # Make the LLM call in a separate thread
            response = await asyncio.to_thread(llm.predict, COMPRESS_AND_FILTER_PROMPT,query=question, text=doc_text)
            summarized_text = response.strip() if response else ""

            if not summarized_text:
                return None

            summarized_node = TextNode(
                id_=text_node.id_,
                text=summarized_text,
                metadata=metadata  # Retain metadata
            )

            return NodeWithScore(
                node=summarized_node,
                score=node_with_score.score
            )

        tasks = [process_document(node) for node in docs]
        results = await asyncio.gather(*tasks)

        return [result for result in results if result is not None]

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


async def main():
    """
    Main function to test chatbot locally in terminal
    """
    rag = RAGSystem()
    relative_directory_path = "../Output/websites/creuto"
    absolute_directory_path = os.path.abspath(relative_directory_path)
    rag.initialize(directory_path=absolute_directory_path)
    print("Welcome!")

    while True:
        usr_input = input("User: ")
        if usr_input == "quit":
            break

        response = await rag.generate_custom_response(usr_input)

        print("Answer:", response["answer"])
        print("Sources:", response["sources"])


if __name__ == "__main__":
    asyncio.run(main())
    # main()
