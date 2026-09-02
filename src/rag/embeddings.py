"""Embedding abstraction with a deterministic CPU-only local implementation."""
import hashlib
import math
import re
from typing import List, Sequence


class EmbeddingError(ValueError):
    pass


class EmbeddingProvider:
    """Interface for interchangeable text embedding implementations."""

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        raise NotImplementedError

    def embed_query(self, query: str) -> List[float]:
        raise NotImplementedError


class HashEmbeddingProvider(EmbeddingProvider):
    """Small deterministic token-hash embedding with no model downloads."""

    def __init__(self, dimension: int = 256):
        if dimension <= 0:
            raise EmbeddingError("embedding dimension must be positive")
        self.dimension = dimension

    def _embed(self, text: str) -> List[float]:
        if not isinstance(text, str) or not text.strip():
            raise EmbeddingError("cannot embed an empty query or document")
        vector = [0.0] * self.dimension
        tokens = re.findall(r"[a-z0-9]+", text.casefold())
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            raise EmbeddingError("text produced no embeddable tokens")
        return [value / norm for value in vector]

    def embed_texts(self, texts: Sequence[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, query: str) -> List[float]:
        return self._embed(query)


__all__ = ["EmbeddingError", "EmbeddingProvider", "HashEmbeddingProvider"]
