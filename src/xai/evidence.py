"""Evidence lookup for the local ingredient knowledge base."""
from typing import Any, Dict, Optional

from src.ingredients import get_ingredient_knowledge, normalize_ingredient

from .models import EvidenceItem


def get_evidence_for_ingredient(value: str) -> Dict[str, Any]:
    """Return available local information without fabricating external evidence.

    The current knowledge base has no verified source records or citations.
    Therefore this function returns ``evidence_available=False`` and an empty
    evidence list, while preserving the matching knowledge source identifier.
    """
    if not isinstance(value, str):
        raise TypeError("ingredient value must be a string")

    normalized = normalize_ingredient(value)
    if not normalized["canonical_name"]:
        return {"evidence_available": False, "evidence": [], "knowledge_source_id": None}

    knowledge = get_ingredient_knowledge(normalized["canonical_name"])
    if knowledge is None:
        return {"evidence_available": False, "evidence": [], "knowledge_source_id": None}

    # The local record is useful context, but it is not presented as verified evidence.
    return {
        "evidence_available": False,
        "evidence": [],
        "knowledge_source_id": f"local-kb:{knowledge['canonical_name']}",
        "unavailable_reason": "No verified source record is present in the local knowledge base.",
    }


__all__ = ["get_evidence_for_ingredient", "EvidenceItem"]
