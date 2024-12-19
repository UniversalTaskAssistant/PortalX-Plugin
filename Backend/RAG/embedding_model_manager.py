import os
from typing import Optional

from llama_index.core import Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI


class EmbeddingModelManager:
    def __init__(self, openai_api_key: str):
        self.openai_api_key = openai_api_key
        self.embed_model: Optional[HuggingFaceEmbedding] = None

    def initialize_models(self, embed_model_name: str, chunk_size: int, chunk_overlap: int):
        self.embed_model = HuggingFaceEmbedding(
            model_name=embed_model_name,
            embed_batch_size=100
        )
        os.environ["OPENAI_API_KEY"] = self.openai_api_key
        Settings.llm = OpenAI(model="gpt-4o")
        Settings.embed_model = self.embed_model
        Settings.chunk_size = chunk_size
        Settings.chunk_overlap = chunk_overlap

    def get_embed_model(self) -> HuggingFaceEmbedding:
        return self.embed_model
