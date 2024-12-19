from typing import List, Dict, Any

from langsmith import traceable
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import NodeWithScore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI
from sklearn.metrics.pairwise import cosine_similarity

from Backend.RAG.citation_manager import process_context_with_citations
from Backend.RAG.prompts import SYSTEM_PROMPT, ANSWER_TEMPLATE


class QueryManager:
    def __init__(self, embed_model: HuggingFaceEmbedding):
        self.embed_model = embed_model

    @traceable(run_type="chain")
    def retrieve_documents(self, index: VectorStoreIndex, question: str, top_k: int = 5) -> List[NodeWithScore]:
        if not index:
            raise ValueError("Index has not been initialized.")
        query_engine = index.as_query_engine(similarity_top_k=top_k)
        response = query_engine.query(question)
        return response.source_nodes

    @traceable(run_type="chain")
    def query(self, index: VectorStoreIndex, question: str, top_k: int = 5) -> Dict[str, Any]:
        retrieved_docs: List[NodeWithScore] = self.retrieve_documents(index, question, top_k=top_k)
        compressed_docs: List[NodeWithScore] = self.compress_and_filter_documents(retrieved_docs, question, self.embed_model)

        processed_context, citation_manager = process_context_with_citations(compressed_docs)

        llm: OpenAI = OpenAI(model="gpt-4o", temperature=0)

        raw_answer = llm.predict(
            SYSTEM_PROMPT,
            question=question,
            context=processed_context
        )

        answer_content = raw_answer
        if '<answer>' in raw_answer and '</answer>' in raw_answer:
            answer_content = raw_answer.split('<answer>')[1].split('</answer>')[0].strip()

        full_html = ANSWER_TEMPLATE.format(answer_content=answer_content)

        return {
            "answer": full_html,
        }

    @traceable(run_type="chain")
    def compress_and_filter_documents(self, docs: List[NodeWithScore], question: str, embed_model: HuggingFaceEmbedding) -> List[NodeWithScore]:
        updated_nodes: List[NodeWithScore] = []
        query_embedding: List[float] = embed_model._get_text_embedding(question)

        for doc in docs:
            splitter = SentenceSplitter(chunk_size=100, chunk_overlap=10)
            split_texts: List[str] = splitter.split_text(doc.node.text)
            embeddings: List[List[float]] = embed_model._get_text_embeddings(split_texts)
            similarities: List[float] = cosine_similarity([query_embedding], embeddings)[0]

            filtered_texts = [
                text for text, similarity in zip(split_texts, similarities) if similarity >= 0.85
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
