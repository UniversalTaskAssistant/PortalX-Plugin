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
    load_index_from_storage,
)
from llama_index.core.indices.base import BaseIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore, TextNode, Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity
from sympy import false

from Backend.RAG.prompts import SYSTEM_PROMPT

class RAGSystem:
    # RAG system for document processing and querying.
    def __init__(self, max_concurrent_tasks: int = 3):
        load_dotenv()
        self.openai_api_key: Optional[str] = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OpenAI API key not found in .env file. Please ensure the file contains the key as OPENAI_API_KEY.")

        self.current_directory_path: Optional[str] = None
        self.embed_model: Optional[HuggingFaceEmbedding] = None
        self.index: Optional[VectorStoreIndex] = None
        self.query_engine: Optional[Any] = None

        self.max_concurrent_tasks: int = max_concurrent_tasks
        self.semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor(max_workers=max_concurrent_tasks)

    async def initialize(
        self,
        directory_path: str,
        embed_model_name: str = "hkunlp/instructor-base",
        chunk_size: int = 1024,
        chunk_overlap: int = 200,
        load_from_disk: bool = True,
        resume_progress: bool = False,
        process_limit: int = -1
    ):
        # Asynchronous initialization.
        self.current_directory_path = directory_path
        self._initialize_models(embed_model_name, chunk_size, chunk_overlap)
        self.text_splitter: SentenceSplitter = SentenceSplitter(chunk_size=300, chunk_overlap=10)

        embedding_dir = os.path.join(directory_path, "embedding")
        if load_from_disk and os.path.exists(embedding_dir) and not resume_progress:
            self.index = await self._load_index_from_disk(directory_path)
        else:
            self.index = await self._create_and_save_indices(
                directory_path,
                resume_progress,
                process_limit
            )

        self.query_engine = self.index.as_query_engine(
            response_mode="tree_summarize",
            similarity_top_k=3,
            streaming=True
        )

    def _initialize_models(self, embed_model_name: str, chunk_size: int, chunk_overlap: int):
        # Initialize embedding model and configure settings.
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
        # Load saved index from disk.
        embedding_dir = os.path.join(directory_path, "embedding")
        print("Loading saved index from disk:", embedding_dir)
        loop = asyncio.get_event_loop()
        storage_context: StorageContext = await loop.run_in_executor(
            self.executor,
            lambda: StorageContext.from_defaults(persist_dir=embedding_dir)
        )
        loaded_index = await loop.run_in_executor(
            self.executor,
            lambda: load_index_from_storage(storage_context)
        )
        return loaded_index

    def _load_progress(self, progress_path: str) -> set:
        # Load progress.
        if os.path.exists(progress_path):
            with open(progress_path, "r") as f:
                return set(json.load(f))
        return set()

    def _save_progress(self, progress_path: str, processed_docs: set):
        # Save progress.
        with open(progress_path, "w") as f:
            json.dump(list(processed_docs), f)

    async def _process_single_document(self, doc: Document) -> Document:
        # Asynchronously process a single document.
        async with self.semaphore:
            print(f"Processing document: {doc.doc_id}")
            return doc

    async def _create_and_save_indices(
            self,
            directory_path: str,
            resume_progress: bool,
            process_limit: int
    ) -> VectorStoreIndex:
        # Create and save indices.
        embedding_dir = os.path.join(directory_path, "embedding")
        embedding_dir = os.path.abspath(embedding_dir)
        os.makedirs(embedding_dir, exist_ok=True)

        progress_path = os.path.join(embedding_dir, "progress.json")
        processed_docs = self._load_progress(progress_path) if resume_progress else set()

        existing_index: Optional[VectorStoreIndex] = None
        loop = asyncio.get_event_loop()

        possible_index_file = os.path.join(embedding_dir, "docstore.json")
        if os.path.exists(possible_index_file):
            print("Found existing index. Loading...")
            storage_context = await loop.run_in_executor(
                self.executor,
                lambda: StorageContext.from_defaults(persist_dir=embedding_dir)
            )
            existing_index = await loop.run_in_executor(
                self.executor,
                lambda: load_index_from_storage(storage_context)
            )
            print("Index loaded successfully.")
        else:
            print("No existing index found. Will create a new one.")

        print("Loading new documents...")
        reader = SimpleDirectoryReader(
            directory_path,
            recursive=True,
            exclude_hidden=True,
            filename_as_id=True,
            exclude=["embedding/**"]
        )

        tasks: List[asyncio.Task] = []
        new_docs: List[Document] = []
        processed_count = 0

        for docs_batch in reader.iter_data(show_progress=True):
            for doc in docs_batch:
                doc_abs_path = os.path.abspath(doc.doc_id)
                if embedding_dir in doc_abs_path:
                    continue

                if process_limit != -1 and processed_count >= process_limit:
                    print(f"Process limit reached: {process_limit} documents.")
                    break

                if doc.doc_id not in processed_docs:
                    task = self._process_single_document(doc)
                    tasks.append(task)
                    processed_count += 1

            if process_limit != -1 and processed_count >= process_limit:
                break

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                print(f"Task {idx} Exception:", res)
            elif isinstance(res, Document):
                new_docs.append(res)
                processed_docs.add(res.doc_id)

        self._save_progress(progress_path, processed_docs)

        print(f"Number of new docs: {len(new_docs)}")

        if existing_index and len(new_docs) > 0:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                lambda: existing_index.insert_nodes(new_docs, show_progress=True)
            )
            await loop.run_in_executor(
                self.executor,
                lambda: existing_index.storage_context.persist(persist_dir=embedding_dir)
            )
            print("Updated existing index with new documents. Saved successfully.")
            return existing_index

        all_docs: List[Document] = new_docs
        print(f"Total documents to build index: {len(all_docs)}")

        if not existing_index:
            loop = asyncio.get_event_loop()
            condensed_index: VectorStoreIndex = await loop.run_in_executor(
                self.executor,
                lambda: VectorStoreIndex.from_documents(all_docs, show_progress=True)
            )
            await loop.run_in_executor(
                self.executor,
                lambda: condensed_index.storage_context.persist(persist_dir=embedding_dir)
            )
            print("Created new index from scratch and saved successfully.")
            return condensed_index
        else:
            print("No new docs to add. Returning existing index as is.")
            return existing_index

    @traceable(run_type="chain")
    def retrieve_documents(self, question: str, top_k: int = 3) -> List[NodeWithScore]:
        # Retrieve documents.
        if not self.index:
            raise ValueError("Index has not been initialized.")
        query_engine = self.index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)
        return response.source_nodes

    @traceable(run_type="chain")
    def query(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        # Generate a response by manually controlling the RAG pipeline.
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
                    "file": doc.node.extra_info.get('file_name', 'Unknown'),
                    "score": round(doc.score, 3) if doc.score else None,
                    "text_chunk": doc.node.text[:200] + "..."
                } for doc in compressed_docs
            ]
        }

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str) -> List[NodeWithScore]:
        # Compress and filter documents using embedding similarity.
        updated_nodes: List[NodeWithScore] = []
        query_embedding: List[float] = self.embed_model._get_text_embedding(question)

        for doc in docs:
            splitter = SentenceSplitter(chunk_size=150, chunk_overlap=10)
            split_texts: List[str] = splitter.split_text(doc.node.text)
            embeddings: List[List[float]] = self.embed_model._get_text_embeddings(split_texts)
            similarities: List[float] = cosine_similarity([query_embedding], embeddings)[0]

            filtered_texts = [
                text for text, similarity in zip(split_texts, similarities) if similarity >= 0.82
            ]
            if filtered_texts:
                combined_text = " ".join(filtered_texts)
                ref_id = getattr(doc.node, "node_id", "unknown_ref_id")

                new_doc = Document(
                    text=combined_text,
                    doc_id=ref_id,
                    extra_info=getattr(doc.node, 'metadata', {})
                )

                updated_nodes.append(
                    NodeWithScore(node=new_doc, score=max(similarities))
                )

        return updated_nodes

    def cleanup(self):
        # Cleanup resources.
        if self.executor:
            self.executor.shutdown()

    @staticmethod
    def format_response(result: Dict[str, Any], show_sources: bool = True) -> str:
        # Format final response.
        output: str = f"Answer: {result['answer']}\n\n"
        if show_sources:
            output += "Sources:\n"
            for idx, source in enumerate(result['sources'], 1):
                output += f"\n{idx}. {source['file']}"
        return output


async def main():
    # Main function to test RAG system locally.
    rag: RAGSystem = RAGSystem(max_concurrent_tasks=5)
    relative_directory_path: str = "../Output/websites/tum-en"
    absolute_directory_path: str = os.path.abspath(relative_directory_path)

    try:
        await rag.initialize(directory_path=absolute_directory_path,
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
