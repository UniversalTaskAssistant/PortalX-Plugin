import json
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from langsmith.run_helpers import traceable

from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    SimpleDirectoryReader,
    Settings,
    load_index_from_storage
)
from llama_index.core.indices.base import BaseIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode, Document
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sympy import false

from Backend.RAG.prompts import SYSTEM_PROMPT

# def extract_text(doc: NodeWithScore) -> Optional[str]:
#     return doc.node.text

class RAGSystem:
    """A Retrieval-Augmented Generation (RAG) system for document processing and querying."""

    def __init__(self, max_concurrent_tasks: int = 3):
        load_dotenv()
        self.openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')

        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

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

    async def initialize(self, directory_path: str, embed_model_name: str = "hkunlp/instructor-base",
                         chunk_size: int = 1024,
                         chunk_overlap: int = 200, load_from_disk: bool = True, resume_progress: bool = True,
                         process_limit: int = -1):
        """
        Initialize the RAG system components asynchronously.

        Args:
            directory_path: Path to document directory
            embed_model_name: Name of the embedding model to use
            chunk_size: Size of text chunks for processing
            chunk_overlap: Overlap between consecutive chunks
            load_from_disk: Whether to load existing index from disk
            resume_progress: Whether to resume from previous progress
            process_limit: Limit the number of documents to process (-1 for no limit)
        """
        self.current_directory_path = directory_path
        self._initialize_models(embed_model_name, chunk_size, chunk_overlap)
        self.text_splitter: SentenceSplitter = SentenceSplitter(chunk_size=150, chunk_overlap=10)

        if load_from_disk and os.path.exists(f"{directory_path}/embedding") and not resume_progress:
            self.index = await self._load_index_from_disk(directory_path)
        else:
            self.index = await self._create_and_save_indices(directory_path, resume_progress, process_limit)

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

    def _load_progress(self, progress_path: str) -> set:
        """Load processing progress from disk."""
        if os.path.exists(progress_path):
            with open(progress_path, "r") as f:
                return set(json.load(f))
        return set()

    def _save_progress(self, progress_path: str, processed_docs: set):
        """Save processing progress to disk."""
        with open(progress_path, "w") as f:
            json.dump(list(processed_docs), f)

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

    async def _create_and_save_indices(self, directory_path: str, resume_progress: bool,
                                       process_limit: int) -> VectorStoreIndex:
        """Create and save indices for each document asynchronously."""
        print("Creating new indices...")
        embedding_dir: str = f"{directory_path}/embedding"
        os.makedirs(embedding_dir, exist_ok=True)

        progress_path = os.path.join(embedding_dir, "progress.json")
        processed_docs = self._load_progress(progress_path) if resume_progress else set()

        reader = SimpleDirectoryReader(
            directory_path,
            recursive=True,
            exclude_hidden=True,
            filename_as_id=True
        )

        tasks: List[asyncio.Task] = []
        all_docs: List[Any] = []
        processed_count = 0

        try:
            for docs in reader.iter_data(show_progress=True):
                for doc in docs:
                    # Skip embedding directory
                    if os.path.commonpath([embedding_dir, doc.doc_id]) == embedding_dir:
                        continue

                    if process_limit != -1 and processed_count >= process_limit:
                        print(f"Process limit reached: {process_limit} documents.")
                        break

                    if doc.doc_id not in processed_docs:
                        task = self._process_single_document(doc, embedding_dir)
                        tasks.append(task)
                        processed_count += 1

                if process_limit != -1 and processed_count >= process_limit:
                    break

            results: List[tuple] = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, tuple):
                    doc, _ = result
                    all_docs.append(doc)
                    processed_docs.add(doc.doc_id)

        finally:
            # Save progress to ensure it is not lost
            self._save_progress(progress_path, processed_docs)

            # Ensure condensed_index is created even if processing was interrupted
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
    def query(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """Generate a response by manually controlling the RAG pipeline."""
        retrieved_docs: List[NodeWithScore] = self.retrieve_documents(question, top_k=top_k)
        compressed_docs: List[NodeWithScore] = self.compress_and_filter_documents(retrieved_docs, question)

        context: str = "\n".join([
            doc.node.text for doc in compressed_docs if doc.node.text
        ])

        llm: OpenAI = OpenAI(model="gpt-4o", temperature=0)
        answer: str = llm.predict(SYSTEM_PROMPT, question=question, context=context)

        return {
            "answer": answer,
            "sources": [
                {
                    "file": doc.metadata.get('file_name', 'Unknown'),
                    "score": round(doc.score, 3) if doc.score else None,
                    "text_chunk": doc.node.text[:200] + "..."
                } for doc in compressed_docs
            ]
        }

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str) -> List[NodeWithScore]:
        """Compress and filter documents using embedding similarity."""
        updated_nodes: List[NodeWithScore] = []

        query_embedding: List[float] = self.embed_model._get_text_embedding(question)

        for doc in docs:
            split_texts: List[str] = self.text_splitter.split_text(doc.node.text)

            embeddings: List[List[float]] = self.embed_model._get_text_embeddings(split_texts)

            similarities: List[float] = cosine_similarity([query_embedding], embeddings)[0]

            filtered_texts = [
                text for text, similarity in zip(split_texts, similarities) if similarity >= 0.85
            ]

            if filtered_texts:
                combined_text = " ".join(filtered_texts)
                updated_node = NodeWithScore(
                    node=TextNode(text=combined_text, **{k: v for k, v in doc.node.__dict__.items() if k != 'text'}),
                    score=max(similarities)
                )

                updated_nodes.append(updated_node)

        return updated_nodes

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
    relative_directory_path: str = "../Output/websites/signavio"
    absolute_directory_path: str = os.path.abspath(relative_directory_path)

    try:
        await rag.initialize(directory_path=absolute_directory_path,resume_progress= True, process_limit=-1)

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
