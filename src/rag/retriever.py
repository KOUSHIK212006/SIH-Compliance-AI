"""Semantic evidence retrieval over the local vector store."""
from typing import Dict, List, Optional

from src.ingredients import get_ingredient_knowledge, normalize_ingredient

from .models import RetrievalResult
from .vector_store import LocalVectorStore


def retrieve_evidence(query: str, vector_store: LocalVectorStore, top_k: int = 5, authority: Optional[str] = None, source_type: Optional[str] = None) -> List[RetrievalResult]:
    """Return ranked evidence chunks; never generate an answer."""
    filters = {}
    if authority is not None:
        filters["authority"] = authority
    if source_type is not None:
        filters["source_type"] = source_type
    return vector_store.similarity_search(query, top_k=top_k, filters=filters or None)


def retrieve_ingredient_evidence(ingredient: str, vector_store: LocalVectorStore, context: Optional[str] = None, top_k: int = 5, authority: Optional[str] = None, source_type: Optional[str] = None) -> List[RetrievalResult]:
    """Retrieve evidence using supplied ingredient and optional product context."""
    normalized = normalize_ingredient(ingredient)
    if not normalized["canonical_name"]:
        raise ValueError("ingredient must not be empty")
    parts = [normalized["canonical_name"]]
    knowledge = get_ingredient_knowledge(normalized["canonical_name"])
    if knowledge:
        parts.extend([knowledge["category"], *knowledge["common_uses"]])
    if context:
        if not isinstance(context, str):
            raise TypeError("context must be a string when supplied")
        parts.append(context.strip())
    parts.extend(["food additive", "food regulation", "permitted use"])
    return retrieve_evidence(" ".join(part for part in parts if part), vector_store, top_k, authority, source_type)


__all__ = ["retrieve_evidence", "retrieve_ingredient_evidence"]
