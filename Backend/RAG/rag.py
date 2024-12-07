import asyncio
from concurrent.futures import ThreadPoolExecutor

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
    def __init__(self,max_concurrent_tasks: int = 3):
        """
        Initialize RAG system with empty components.
        """

        load_dotenv()
        self.openai_api_key = os.getenv('OPENAI_API_KEY')

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

        self.current_directory_path = None  # Path to the currently loaded directory
        self.embed_model = None            # Initialize embedding model
        self.documents = None              # Placeholder for documents
        self.index = None                  # Vector store index
        self.query_engine = None           # Query engine with response synthesis
        self.max_concurrent_tasks = max_concurrent_tasks
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)

    async def initialize(self,
                         directory_path: str,
                         embed_model_name: str = "BAAI/bge-small-en-v1.5",
                         chunk_size: int = 1024,
                         chunk_overlap: int = 200,
                         load_from_disk: bool = True):
        """
        Initialize the RAG system components asynchronously.

        Args:
            directory_path: Path to document directory
            embed_model_name: Name of the embedding model to use
            chunk_size: Size of text chunks for processing
            chunk_overlap: Overlap between consecutive chunks
            load_from_disk: Whether to load existing index from disk
        """
        self.current_directory_path = directory_path
        self._initialize_models(embed_model_name, chunk_size, chunk_overlap)

        if load_from_disk and os.path.exists(f"{directory_path}/embedding"):
            self.index = await self._load_index_from_disk(directory_path)
        else:
            self.index = await self._create_and_save_indices(directory_path)

        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

    def _initialize_models(self, embed_model_name: str, chunk_size: int, chunk_overlap: int):
        """Initialize embedding model and configure settings."""
        self.embed_model = HuggingFaceEmbedding(
            model_name=embed_model_name,
            embed_batch_size=100
        )
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        Settings.llm = OpenAI(model="gpt-4")
        Settings.embed_model = self.embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

    async def _load_index_from_disk(self, directory_path: str):
        """
        Load saved index from disk asynchronously.

        Args:
            directory_path: Path to the directory containing the index
        """
        print("Loading saved index from disk...")
        from llama_index.core import StorageContext, load_index_from_storage

        loop = asyncio.get_event_loop()
        storage_context = await loop.run_in_executor(
            self.executor,
            lambda: StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
        )

        return await loop.run_in_executor(
            self.executor,
            lambda: load_index_from_storage(storage_context)
        )

    async def _process_single_document(self, doc, embedding_dir: str) -> tuple:
        """
        Process a single document asynchronously - create and save its index.

        Args:
            doc: Document to process
            embedding_dir: Directory to store embeddings

        Returns:
            Tuple of (processed document, document index)
        """
        async with self.semaphore:
            print(f"Processing document: {doc.doc_id}")

            # Calculate relative path and create directories
            relative_path = doc.doc_id.replace(self.current_directory_path + '/', '')
            doc_path = os.path.join(embedding_dir, relative_path)
            os.makedirs(os.path.dirname(doc_path), exist_ok=True)

            # Create document index in thread pool
            loop = asyncio.get_event_loop()
            doc_index = await loop.run_in_executor(
                self.executor,
                lambda: VectorStoreIndex.from_documents([doc], show_progress=True)
            )

            # Save individual document index
            await loop.run_in_executor(
                self.executor,
                lambda: doc_index.storage_context.persist(persist_dir=doc_path)
            )

            print(f"Index saved for {doc.doc_id}")
            return doc, doc_index

    async def _create_and_save_indices(self, directory_path: str):
        """
        Create and save indices for each document asynchronously while maintaining a condensed index.

        Args:
            directory_path: Path to the directory containing documents

        Returns:
            Condensed index combining all documents
        """
        print("Creating new indices...")
        embedding_dir = f"{directory_path}/embedding"
        os.makedirs(embedding_dir, exist_ok=True)

        # Initialize document reader
        reader = SimpleDirectoryReader(
            directory_path,
            recursive=True,
            exclude_hidden=True,
            filename_as_id=True
        )

        # Process documents concurrently
        tasks = []
        all_docs = []

        for docs in reader.iter_data(show_progress=True):
            for doc in docs:
                task = self._process_single_document(doc, embedding_dir)
                tasks.append(task)

        # Wait for all documents to be processed
        results = await asyncio.gather(*tasks)

        # Collect processed documents
        for doc, _ in results:
            all_docs.append(doc)

        # Create and save condensed index
        loop = asyncio.get_event_loop()
        condensed_index = await loop.run_in_executor(
            self.executor,
            lambda: VectorStoreIndex.from_documents(all_docs, show_progress=True)
        )

        await loop.run_in_executor(
            self.executor,
            lambda: condensed_index.storage_context.persist(persist_dir=embedding_dir)
        )

        print("Condensed index saved successfully")
        return condensed_index

    def cleanup(self):
        """Clean up resources used by the async system."""
        if self.executor:
            self.executor.shutdown()

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
        #TODO
        # llm = OpenAI(model="gpt-4", temperature=0)
        # compressed_docs = await self.compress_and_filter_documents(retrieved_docs, question, llm)

        # Step 3: Construct context
        # context = "\n".join([doc.text for doc in compressed_docs])
        context = "\n".join([doc.text for doc in retrieved_docs])

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
                } for doc in retrieved_docs
            ]
        }

    # return {
    #     "answer": answer,
    #     "sources": [
    #         {
    #             "file": doc.metadata.get('file_name', 'Unknown'),
    #             "score": round(doc.score, 3) if doc.score else None,
    #             "text_chunk": doc.text[:200] + "..."
    #         } for doc in compressed_docs
    #     ]
    # }

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

    rag = RAGSystem(max_concurrent_tasks=3)
    relative_directory_path = "../Output/websites/signavio"
    absolute_directory_path = os.path.abspath(relative_directory_path)
    try:
        await rag.initialize(
            directory_path=absolute_directory_path  # Create new indices
        )
        # Use the system...
    finally:
        rag.cleanup()

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
