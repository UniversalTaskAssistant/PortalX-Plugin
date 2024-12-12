# Standard library imports
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

# Third-party imports
from dotenv import load_dotenv
from langsmith.run_helpers import traceable

# LlamaIndex imports
from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    load_index_from_storage
)
from llama_index.core.indices.base import BaseIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

# Local imports
from Backend.RAG.prompts import SYSTEM_PROMPT


def extract_text(doc: NodeWithScore) -> Optional[str]:
    """
    Safely extract text from a NodeWithScore object.

    Args:
        doc: NodeWithScore object.

    Returns:
        The text content if the node contains a text field, None otherwise.
    """
    return doc.node.text

class RAGSystem:
    """A Retrieval-Augmented Generation (RAG) system for document processing and querying."""

    def __init__(self, max_concurrent_tasks: int = 3):
        """
        Initialize RAG system with empty components.

        Args:
            max_concurrent_tasks: Maximum number of concurrent tasks to process
        """
        load_dotenv()
        self.openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')

        if not self.openai_api_key:
            raise ValueError(
                "OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

        # System components
        self.current_directory_path: Optional[str] = None
        self.embed_model: Optional[HuggingFaceEmbedding] = None
        self.documents: Optional[List[Any]] = None
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine: Optional[Any] = None

        # Concurrency controls
        self.max_concurrent_tasks: int = max_concurrent_tasks
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)

    async def initialize(self,
                         directory_path: str,
                         embed_model_name: str = "hkunlp/instructor-base",
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
        self.text_splitter: SentenceSplitter = SentenceSplitter(chunk_size=150, chunk_overlap=10)
        # self.text_splitter: HTMLNodeParser = HTMLNodeParser()

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
        Settings.llm = OpenAI(model="gpt-4o")
        Settings.embed_model = self.embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

    async def _load_index_from_disk(self, directory_path: str) -> BaseIndex:
        """Load saved index from disk asynchronously."""
        print("Loading saved index from disk...")

        loop = asyncio.get_event_loop()
        storage_context: StorageContext = await loop.run_in_executor(
            self.executor,
            lambda: StorageContext.from_defaults(persist_dir=f"{directory_path}/embedding")
        )

        return await loop.run_in_executor(
            self.executor,
            lambda: load_index_from_storage(storage_context)
        )

    async def _process_single_document(self, doc: Any, embedding_dir: str) -> tuple:
        """Process a single document asynchronously - create and save its index."""
        async with self.semaphore:
            print(f"Processing document: {doc.doc_id}")

            relative_path: str = doc.doc_id.replace(self.current_directory_path + '/', '')
            doc_path: str = os.path.join(embedding_dir, relative_path)
            os.makedirs(os.path.dirname(doc_path), exist_ok=True)

            loop = asyncio.get_event_loop()
            doc_index: VectorStoreIndex = await loop.run_in_executor(
                self.executor,
                lambda: VectorStoreIndex.from_documents([doc], show_progress=True)
            )

            await loop.run_in_executor(
                self.executor,
                lambda: doc_index.storage_context.persist(persist_dir=doc_path)
            )

            print(f"Index saved for {doc.doc_id}")
            return doc, doc_index

    async def _create_and_save_indices(self, directory_path: str) -> VectorStoreIndex:
        """Create and save indices for each document asynchronously."""
        print("Creating new indices...")
        embedding_dir: str = f"{directory_path}/embedding"
        os.makedirs(embedding_dir, exist_ok=True)

        reader = SimpleDirectoryReader(
            directory_path,
            recursive=True,
            exclude_hidden=True,
            filename_as_id=True
        )

        tasks: List[asyncio.Task] = []
        all_docs: List[Any] = []

        for docs in reader.iter_data(show_progress=True):
            for doc in docs:
                task = self._process_single_document(doc, embedding_dir)
                tasks.append(task)

        results: List[tuple] = await asyncio.gather(*tasks)

        for doc, _ in results:
            all_docs.append(doc)

        loop = asyncio.get_event_loop()
        condensed_index: VectorStoreIndex = await loop.run_in_executor(
            self.executor,
            lambda: VectorStoreIndex.from_documents(all_docs, show_progress=True)
        )

        await loop.run_in_executor(
            self.executor,
            lambda: condensed_index.storage_context.persist(persist_dir=embedding_dir)
        )

        print("Condensed index saved successfully")
        return condensed_index

    @traceable(run_type="chain")
    def retrieve_documents(self, question: str, top_k: int = 3) -> List[NodeWithScore]:
        """Retrieve relevant documents and compress/filter them."""
        if not self.index:
            raise ValueError("Index has not been initialized.")

        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)
        return response.source_nodes

    @traceable(run_type="chain")
    def generate_custom_response(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Generate a response by manually controlling the RAG pipeline."""
        # Step 1: Retrieve documents
        retrieved_docs: List[NodeWithScore] = self.retrieve_documents(question, top_k=top_k)

        # Step 2: Compress and filter documents
        compressed_docs: List[NodeWithScore] = self.compress_and_filter_documents(retrieved_docs, question)

        # Step 3: Construct context
        context: str = "\n".join([
            extract_text(doc) for doc in compressed_docs if extract_text(doc)
        ])

        # context = "\n".join([doc.text for doc in compressed_docs])
        # context = "\n".join([doc.text for doc in retrieved_docs])

        # context: str = "\n".join([
        #     extract_text(doc) for doc in retrieved_docs if extract_text(doc)
        # ])

        # Step 4: Use custom prompt to generate response
        llm: OpenAI = OpenAI(model="gpt-4o", temperature=0)
        answer: str = llm.predict(SYSTEM_PROMPT, question=question, context=context)

        # Alternative response format with compressed docs:
        # return {
        #     "answer": answer,
        #     "sources": [
        #         {
        #             "file": doc.metadata.get('file_name', 'Unknown'),
        #             "score": round(doc.score, 3) if doc.score else None,
        #             "text_chunk": extract_text(doc)[:200] + "..."
        #         } for doc in retrieved_docs
        #     ]
        # }

        return {
            "answer": answer,
            "sources": [
                {
                    "file": doc.metadata.get('file_name', 'Unknown'),
                    "score": round(doc.score, 3) if doc.score else None,
                    "text_chunk": extract_text(doc)[:200] + "..."
                } for doc in compressed_docs
            ]
        }

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str) -> List[NodeWithScore]:
        """使用 HuggingFace Embedding 的相似性来分块、压缩和过滤文档。"""

        # Step 1: Parse the documents into nodes
        split_texts: List[str] = []
        for doc in docs:
            split_texts.extend(self.text_splitter.split_text(doc.node.text))


        # Step 2: 生成 embeddings
        query_embedding: List[float] = self.embed_model._get_text_embedding(question)
        embeddings: List[List[float]] = self.embed_model._get_text_embeddings(split_texts)

        # Step 3: 计算相似性并过滤
        similarities: List[float] = cosine_similarity([query_embedding], embeddings)[0]
        filtered_texts: List[str] = [
            text for text, similarity in zip(split_texts, similarities) if similarity >= 0.85
        ]

        # Step 4: 构造 NodeWithScore 对象
        filtered_nodes: List[NodeWithScore] = [
            NodeWithScore(
                node=TextNode(text=text),
                score=similarity
            )
            for text, similarity in zip(filtered_texts, similarities) if similarity >= 0.85
        ]

        return filtered_nodes

    def cleanup(self):
        """Clean up resources used by the async system."""
        if self.executor:
            self.executor.shutdown()

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = True) -> str:
        """Format the query response into a readable string."""
        output: str = f"Answer: {result['answer']}\n\n"
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result['sources'], 1):
                output += f"\n{idx}. {source['file']}"
        return output


async def main():
    """Main function to test chatbot locally in terminal."""
    rag: RAGSystem = RAGSystem(max_concurrent_tasks=3)
    relative_directory_path: str = "../Output/websites/nsw"
    absolute_directory_path: str = os.path.abspath(relative_directory_path)

    try:
        await rag.initialize(directory_path=absolute_directory_path)

        print("Welcome!")
        while True:
            usr_input: str = input("User: ")
            if usr_input == "quit":
                break

            response: Dict[str, Any] = rag.generate_custom_response(usr_input, 5)
            print("Answer:", response["answer"])
            print("Sources:", response["sources"])

    finally:
        rag.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
