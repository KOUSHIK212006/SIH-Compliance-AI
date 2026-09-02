"""Deterministic in-memory store for structured regulatory evidence."""
import copy
import hashlib
from typing import Dict, List, Optional

from .models import EvidenceSearchResult, RegulatoryEvidence


class EvidenceStoreError(Exception):
    pass


class EvidenceStore:
    """Replaceable evidence-store abstraction for local development data."""

    def __init__(self):
        self._records: Dict[str, RegulatoryEvidence] = {}

    @staticmethod
    def _id(record: RegulatoryEvidence) -> str:
        value = "|".join([record.ingredient, record.document_id, record.section or "", str(record.page or ""), record.text])
        return record.evidence_id or "evidence:" + hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

    def add_evidence(self, evidence: RegulatoryEvidence) -> RegulatoryEvidence:
        if not isinstance(evidence, RegulatoryEvidence):
            raise EvidenceStoreError("evidence must be a RegulatoryEvidence record")
        evidence.evidence_id = self._id(evidence)
        if evidence.evidence_id in self._records:
            raise EvidenceStoreError(f"duplicate evidence: {evidence.evidence_id}")
        self._records[evidence.evidence_id] = copy.deepcopy(evidence)
        return copy.deepcopy(evidence)

    def get_evidence(self, evidence_id: str) -> Optional[RegulatoryEvidence]:
        return copy.deepcopy(self._records.get(evidence_id))

    def remove_evidence(self, evidence_id: str) -> bool:
        return self._records.pop(evidence_id, None) is not None

    def list_evidence(self) -> List[RegulatoryEvidence]:
        return [copy.deepcopy(self._records[key]) for key in sorted(self._records)]

    def search_evidence(self, query: str, ingredient: Optional[str] = None) -> List[EvidenceSearchResult]:
        if not isinstance(query, str) or not query.strip():
            raise EvidenceStoreError("query must be a non-empty string")
        query_terms = set(query.casefold().split())
        ingredient_key = ingredient.casefold().strip() if isinstance(ingredient, str) else None
        scored = []
        for record in self._records.values():
            names = {record.ingredient.casefold(), *(alias.casefold() for alias in record.ingredient_aliases)}
            if ingredient_key and ingredient_key not in names:
                continue
            haystack = " ".join([record.ingredient, *record.ingredient_aliases, record.source_title, record.text]).casefold()
            terms = set(haystack.split())
            score = len(query_terms & terms) / len(query_terms) if query_terms else 0.0
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: (-item[0], self._id(item[1])))
        return [EvidenceSearchResult(copy.deepcopy(record), float(score)) for score, record in scored]


__all__ = ["EvidenceStore", "EvidenceStoreError"]
