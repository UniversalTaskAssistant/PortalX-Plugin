from typing import Dict, Any, List

from llama_index.core.schema import NodeWithScore


def extract_url_from_path(file_path: str) -> str:
   try:
       start_index = file_path.find("www")
       if start_index != -1:
           url = file_path[start_index:]
           if url.endswith('.html'):
               url = url[:-5]
           return f"https://{url}"
       return file_path
   except Exception:
       return file_path

class CitationManager:
    def __init__(self):
        self.sources: Dict[str, Dict[str, Any]] = {}
        self.current_citation_id = 1

    def add_source(self, node: NodeWithScore) -> int:
        citation_id = self.current_citation_id
        file_path = node.node.metadata.get("file_path", "")
        url = extract_url_from_path(file_path)

        self.sources[str(citation_id)] = {
            "id": node.node.doc_id,
            "file_name": node.node.metadata.get("file_name", "Unknown"),
            "url": url,
            "score": round(node.score, 3) if node.score else None,
            "text_chunk": node.node.text[:200] + "..."
        }
        self.current_citation_id += 1
        return citation_id


def process_context_with_citations(nodes: List[NodeWithScore]) -> tuple[str, CitationManager]:
    citation_manager = CitationManager()
    processed_texts = []

    for node in nodes:
        citation_id = citation_manager.add_source(node)
        file_path = node.node.metadata.get("file_path", "")
        url = extract_url_from_path(file_path)

        processed_text = (
            f'{node.node.text}[CITE_{citation_id}_{url}]'
        )
        processed_texts.append(processed_text)

    return ' '.join(processed_texts), citation_manager