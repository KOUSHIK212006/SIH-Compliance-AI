"""Data models used by the local RAG retrieval foundation."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentMetadata:
    document_id: str
    title: str
    source: str
    source_type: str
    authority: Optional[str] = None
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None
    version: Optional[str] = None
    regulation: Optional[str] = None
    section: Optional[str] = None
    page: Optional[int] = None
    url: Optional[str] = None
    checksum: Optional[str] = None
    language: Optional[str] = "en"
    amendment_number: Optional[str] = None
    supersedes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceChunk:
    chunk_id: str
    document_id: str
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    page: Optional[int] = None
    section: Optional[str] = None
    source: Optional[str] = None
    authority: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResult:
    chunk: EvidenceChunk
    score: float
    rank: int
    retrieval_method: str = "cosine_similarity"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk": self.chunk.to_dict(),
            "score": self.score,
            "rank": self.rank,
            "retrieval_method": self.retrieval_method,
        }
