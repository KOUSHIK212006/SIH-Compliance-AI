"""Simple persistent local vector store behind a replaceable abstraction."""
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

from .embeddings import EmbeddingProvider, HashEmbeddingProvider
from .models import EvidenceChunk, RetrievalResult


class VectorStoreError(Exception):
    pass


class LocalVectorStore:
    """JSON-persistent vector store suitable for deterministic prototype data."""

    def __init__(self, path: str, embedding_provider: Optional[EmbeddingProvider] = None):
        self.path = Path(path)
        self.embedding_provider = embedding_provider or HashEmbeddingProvider()
        self._records: List[Dict[str, Any]] = []

    def add_documents(self, chunks: List[EvidenceChunk]) -> None:
        if not isinstance(chunks, list):
            raise VectorStoreError("chunks must be a list")
        embeddings = self.embedding_provider.embed_texts([chunk.text for chunk in chunks]) if chunks else []
        by_id = {record["chunk"]["chunk_id"]: record for record in self._records}
        for chunk, embedding in zip(chunks, embeddings):
            by_id[chunk.chunk_id] = {"chunk": chunk.to_dict(), "embedding": embedding}
        self._records = [by_id[key] for key in sorted(by_id)]

    def persist(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps({"records": self._records}, indent=2, sort_keys=True), encoding="utf-8")
        except Exception as exc:
            raise VectorStoreError(f"could not persist vector store: {exc}") from exc

    def load(self) -> None:
        if not self.path.exists():
            raise VectorStoreError(f"vector store not found: {self.path}")
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            records = payload.get("records")
            if not isinstance(records, list):
                raise ValueError("records must be a list")
            self._records = records
        except Exception as exc:
            raise VectorStoreError(f"could not load vector store: {exc}") from exc

    def similarity_search(self, query: str, top_k: int = 5, filters: Optional[Dict[str, str]] = None) -> List[RetrievalResult]:
        if not isinstance(query, str) or not query.strip():
            raise VectorStoreError("query must be a non-empty string")
        if top_k <= 0:
            raise VectorStoreError("top_k must be positive")
        if not self._records:
            raise VectorStoreError("vector store is empty; add documents or load an index first")
        query_vector = self.embedding_provider.embed_query(query)
        scored = []
        for record in self._records:
            chunk_data = record.get("chunk", {})
            metadata = chunk_data.get("metadata", {})
            if filters and any(metadata.get(key) != value for key, value in filters.items()):
                continue
            vector = record.get("embedding", [])
            score = sum(a * b for a, b in zip(query_vector, vector))
            chunk = EvidenceChunk(**chunk_data)
            scored.append((score, chunk))
        scored.sort(key=lambda item: (-item[0], item[1].chunk_id))
        return [RetrievalResult(chunk=chunk, score=float(score), rank=index, retrieval_method="cosine_similarity") for index, (score, chunk) in enumerate(scored[:top_k], start=1)]


__all__ = ["LocalVectorStore", "VectorStoreError"]
