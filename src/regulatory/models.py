"""Data models for structured regulatory evidence."""
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


SOURCE_TYPES = {"regulation", "official_guidance", "scientific_reference", "government_document", "demo"}
EVIDENCE_TYPES = {"permitted", "restricted", "prohibited", "usage_condition", "labeling_requirement", "allergen", "safety_information", "general_information", "unknown"}


@dataclass
class RegulatoryEvidence:
    """One provenance-preserving evidence record."""

    ingredient: str
    ingredient_aliases: List[str]
    source_title: str
    source_type: str
    authority: str
    document_id: str
    section: Optional[str]
    page: Optional[int]
    text: str
    jurisdiction: Optional[str]
    effective_date: Optional[str]
    source_url: Optional[str]
    evidence_type: str
    confidence: float
    notes: Optional[str] = None
    evidence_id: Optional[str] = None

    def __post_init__(self):
        if not isinstance(self.ingredient, str) or not self.ingredient.strip():
            raise ValueError("ingredient must be a non-empty string")
        if not isinstance(self.source_title, str) or not self.source_title.strip():
            raise ValueError("source_title must be a non-empty string")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("text must be a non-empty string")
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source_type: {self.source_type}")
        if self.evidence_type not in EVIDENCE_TYPES:
            raise ValueError(f"unsupported evidence_type: {self.evidence_type}")
        if not isinstance(self.confidence, (int, float)) or not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        if self.page is not None and (not isinstance(self.page, int) or self.page <= 0):
            raise ValueError("page must be a positive integer or None")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceSearchResult:
    """Evidence record with a deterministic matching score."""

    evidence: RegulatoryEvidence
    score: float

    def to_dict(self) -> Dict[str, Any]:
        result = self.evidence.to_dict()
        result["retrieval_score"] = self.score
        return result
