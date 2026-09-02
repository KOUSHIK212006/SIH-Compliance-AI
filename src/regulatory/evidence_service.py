"""Service functions for local structured regulatory evidence."""
from typing import Any, Dict, List, Optional

from src.ingredients import get_ingredient_knowledge, normalize_ingredient

from .evidence_store import EvidenceStore, EvidenceStoreError
from .models import RegulatoryEvidence


def load_demo_evidence(store: Optional[EvidenceStore] = None) -> EvidenceStore:
    """Create a store containing clearly labeled non-regulatory test data."""
    store = store or EvidenceStore()
    store.add_evidence(RegulatoryEvidence(
        ingredient="demo additive", ingredient_aliases=["demo additive", "demo e100"],
        source_title="Demo Regulatory Document", source_type="demo", authority="TEST AUTHORITY",
        document_id="TEST-DOC-001", section="TEST SECTION", page=1,
        text="TEST DATA ONLY: demo additive is included to exercise evidence retrieval.",
        jurisdiction="TEST JURISDICTION", effective_date=None, source_url=None,
        evidence_type="general_information", confidence=0.5,
        notes="DEMO DATA ONLY; not an official regulatory statement.",
    ))
    return store


def add_evidence(store: EvidenceStore, evidence: RegulatoryEvidence) -> Dict[str, Any]:
    """Add one validated evidence record."""
    return store.add_evidence(evidence).to_dict()


def get_evidence(store: EvidenceStore, evidence_id: str) -> Optional[Dict[str, Any]]:
    record = store.get_evidence(evidence_id)
    return record.to_dict() if record else None


def remove_evidence(store: EvidenceStore, evidence_id: str) -> bool:
    return store.remove_evidence(evidence_id)


def list_evidence(store: EvidenceStore) -> List[Dict[str, Any]]:
    return [record.to_dict() for record in store.list_evidence()]


def match_ingredient(store: EvidenceStore, ingredient: str) -> List[Dict[str, Any]]:
    """Find evidence by normalized name, explicit aliases, or supported code."""
    normalized = normalize_ingredient(ingredient)
    if not normalized["canonical_name"]:
        return []
    candidate = normalized["canonical_name"]
    knowledge = get_ingredient_knowledge(candidate)
    candidates = {candidate}
    if knowledge:
        candidates.update(alias.casefold() for alias in knowledge["aliases"])
        candidates.update(code.casefold() for code in knowledge["additive_codes"])
    matches = []
    for value in candidates:
        matches.extend(store.search_evidence(value, ingredient=value))
    unique = {result.evidence.evidence_id: result for result in matches}
    return [result.to_dict() for result in sorted(unique.values(), key=lambda item: (-item.score, item.evidence.evidence_id or ""))]


def search_evidence(store: EvidenceStore, query: str, ingredient: Optional[str] = None) -> Dict[str, Any]:
    """Search evidence and return an explicit no-evidence state when empty."""
    results = store.search_evidence(query, ingredient=ingredient)
    if not results:
        return {"status": "insufficient_evidence", "evidence": [], "message": "No authoritative evidence available."}
    return {"status": "evidence_found", "evidence": [result.to_dict() for result in results], "message": "Evidence retrieved from the configured local store."}


__all__ = ["add_evidence", "get_evidence", "search_evidence", "match_ingredient", "remove_evidence", "list_evidence", "load_demo_evidence"]
