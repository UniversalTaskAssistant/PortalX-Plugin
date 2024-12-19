import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langsmith.run_helpers import traceable

from llama_index.core import (
    VectorStoreIndex
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore
from sympy import false

from Backend.RAG.embedding_model_manager import EmbeddingModelManager
from Backend.RAG.index_manager import IndexManager
from Backend.RAG.query_manager import QueryManager


class RAGSystem:
    # RAG system for document processing and querying.
    def __init__(self, max_concurrent_tasks: int = 3):
        load_dotenv()
        self.openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

        self.current_directory_path: Optional[str] = None
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine: Optional[Any] = None

        self.max_concurrent_tasks: int = max_concurrent_tasks
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)

        self.embedding_manager = EmbeddingModelManager(self.openai_api_key)
        self.index_manager = IndexManager(self.semaphore, self.executor)
        self.query_manager: Optional[QueryManager] = None

    def initialize(
            self,
            directory_path: str,
            embed_model_name: str = "hkunlp/instructor-base",
            chunk_size: int = 1024,
            chunk_overlap: int = 200,
            load_from_disk: bool = True,
            resume_progress: bool = False,
            process_limit: int = -1
    ):
        def run_async_init():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self._initialize_async(
                    directory_path,
                    embed_model_name,
                    chunk_size,
                    chunk_overlap,
                    load_from_disk,
                    resume_progress,
                    process_limit
                ))
            finally:
                loop.close()

        import threading
        thread = threading.Thread(target=run_async_init)
        thread.start()
        thread.join()

    async def _initialize_async(
            self,
            directory_path: str,
            embed_model_name: str,
            chunk_size: int,
            chunk_overlap: int,
            load_from_disk: bool,
            resume_progress: bool,
            process_limit: int
    ):
        self.current_directory_path = directory_path
        self.embedding_manager.initialize_models(embed_model_name, chunk_size, chunk_overlap)
        self.text_splitter: SentenceSplitter = SentenceSplitter(chunk_size=300, chunk_overlap=10)

        embedding_dir = os.path.join(directory_path, "embedding")
        if load_from_disk and os.path.exists(embedding_dir) and not resume_progress:
            self.index = await self.index_manager.load_index_from_disk(directory_path)
        else:
            self.index = await self.index_manager.create_and_save_indices(
                directory_path,
                resume_progress,
                process_limit,
                self.embedding_manager.get_embed_model()
            )

        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

        self.query_manager = QueryManager(self.embedding_manager.get_embed_model())

        return self.index

    @traceable(run_type="chain")
    def retrieve_documents(self, question: str, top_k: int = 5) -> List[NodeWithScore]:
        return self.query_manager.retrieve_documents(self.index, question, top_k=top_k)

    @traceable(run_type="chain")
    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        return self.query_manager.query(self.index, question, top_k=top_k)

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str) -> List[NodeWithScore]:
        return self.query_manager.compress_and_filter_documents(docs, question, self.embedding_manager.get_embed_model())

    def cleanup(self):
        if self.executor:
            self.executor.shutdown()

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = false) -> str:
        output: str = f"Answer: {result['answer']}\n\n"
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result.get('sources', []), 1):
                output += f"\n{idx}. {source['file']}"
        return output


async def main():
    # Main function to test RAG system locally.
    rag: RAGSystem = RAGSystem(max_concurrent_tasks=5)
    relative_directory_path: str = "../Output/websites/tum-en"
    absolute_directory_path: str = os.path.abspath(relative_directory_path)

    try:
        rag.initialize(directory_path=absolute_directory_path,
                       process_limit=-1,
                       resume_progress=True)

        print("Welcome!")
        while True:
            usr_input: str = input("User: ")
            if usr_input.lower() == "quit":
                break

            response: Dict[str, Any] = rag.query(usr_input, 5)
            print(rag.format_response(response))

    finally:
        rag.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
