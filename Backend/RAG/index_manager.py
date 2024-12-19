import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List

from llama_index.core import StorageContext, load_index_from_storage, Document, VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.indices.base import BaseIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding


class IndexManager:
    def __init__(self, semaphore: asyncio.Semaphore, executor: ThreadPoolExecutor):
        self.semaphore = semaphore
        self.executor = executor

    async def load_index_from_disk(self, directory_path: str) -> BaseIndex:
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

    def load_progress(self, progress_path: str) -> set:
        if os.path.exists(progress_path):
            with open(progress_path, "r") as f:
                return set(json.load(f))
        return set()

    def save_progress(self, progress_path: str, processed_docs: set):
        with open(progress_path, "w") as f:
            json.dump(list(processed_docs), f)

    async def process_single_document(self, doc: Document) -> Document:
        async with self.semaphore:
            print(f"Processing document: {doc.doc_id}")
            return doc

    async def create_and_save_indices(
        self,
        directory_path: str,
        resume_progress: bool,
        process_limit: int,
        embed_model: HuggingFaceEmbedding
    ) -> VectorStoreIndex:
        embedding_dir = os.path.join(directory_path, "embedding")
        embedding_dir = os.path.abspath(embedding_dir)
        os.makedirs(embedding_dir, exist_ok=True)

        progress_path = os.path.join(embedding_dir, "progress.json")
        processed_docs = self.load_progress(progress_path) if resume_progress else set()

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
                    task = self.process_single_document(doc)
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

        self.save_progress(progress_path, processed_docs)

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
