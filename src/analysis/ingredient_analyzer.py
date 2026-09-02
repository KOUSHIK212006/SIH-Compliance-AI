"""Deterministic consumer-oriented ingredient analysis.

The profiles in this module are development data for educational prototype
use. They are not medical advice, verified evidence, or legal conclusions.
Confidence values describe profile completeness only; they are not
statistical or medically validated probabilities.
"""
import copy
from typing import Any, Dict, List, Optional, Union

from src.ingredients import get_ingredient_knowledge, normalize_ingredient


EVIDENCE_STATUS = "development_demo"
CONCERN_LEVELS = {"low", "moderate", "high", "unknown"}


_ANALYSIS_PROFILES: Dict[str, Dict[str, Any]] = {
    "sugar": {
        "function": "sweetening",
        "consumer_summary": "A sweetening ingredient commonly used to provide sweetness.",
        "potential_concerns": [],
        "concern_level": "low",
    },
    "salt": {
        "function": "seasoning",
        "consumer_summary": "A seasoning ingredient commonly used to provide flavor.",
        "potential_concerns": [],
        "concern_level": "low",
    },
    "citric acid": {
        "function": "acidity regulation and flavoring",
        "consumer_summary": "An acidulant commonly used to provide acidity and flavor.",
        "potential_concerns": [],
        "concern_level": "low",
    },
    "sodium benzoate": {
        "function": "preservation",
        "consumer_summary": "A preservative used to help maintain product quality during storage.",
        "potential_concerns": [
            {
                "topic": "ingredient context",
                "explanation": "Consumers may want to understand why a preservative is present and how it is used in the product.",
                "context": "Context-dependent; the available development profile does not establish a health conclusion.",
                "evidence_status": EVIDENCE_STATUS,
            }
        ],
        "concern_level": "unknown",
    },
    "ascorbic acid": {
        "function": "antioxidant and flour treatment",
        "consumer_summary": "An ingredient used to help protect food quality and support processing.",
        "potential_concerns": [],
        "concern_level": "low",
    },
    "milk powder": {
        "function": "dairy solids and texture",
        "consumer_summary": "Dried milk used to provide dairy solids and texture.",
        "potential_concerns": [
            {
                "topic": "ingredient context",
                "explanation": "Consumers may want to review the product context when dairy ingredients are relevant to their needs.",
                "context": "Context-dependent; this development profile does not provide medical advice.",
                "evidence_status": EVIDENCE_STATUS,
            }
        ],
        "concern_level": "unknown",
    },
    "cocoa butter": {
        "function": "fat ingredient and confectionery texture",
        "consumer_summary": "A cocoa-derived fat used in confectionery and other food products.",
        "potential_concerns": [],
        "concern_level": "low",
    },
}


def _unknown_result(raw: str, canonical_name: str) -> Dict[str, Any]:
    return {
        "raw": raw,
        "canonical_name": canonical_name,
        "status": "unknown",
        "category": None,
        "function": None,
        "common_uses": [],
        "consumer_summary": "Insufficient information for a development analysis.",
        "potential_concerns": [
            {
                "topic": "insufficient information",
                "explanation": "The ingredient was not identified in the local development knowledge base.",
                "context": "Requires further review; no health or regulatory conclusion is made.",
                "evidence_status": EVIDENCE_STATUS,
            }
        ],
        "concern_level": "unknown",
        "evidence_status": EVIDENCE_STATUS,
        "confidence": 0.1,
        "requires_review": True,
    }


def get_analysis_profile(canonical_name: str) -> Optional[Dict[str, Any]]:
    """Return a copy of the local profile for a canonical ingredient name."""
    if not isinstance(canonical_name, str):
        raise TypeError("canonical_name must be a string")
    return copy.deepcopy(_ANALYSIS_PROFILES.get(canonical_name.casefold()))


def analyze_ingredient(value: Union[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Analyze an ingredient name or normalized ingredient record.

    Empty normalized values return ``None``. Unknown non-empty values return
    a structured result with low confidence and ``requires_review=True``.
    """
    if isinstance(value, dict):
        raw = value.get("raw", value.get("canonical_name", ""))
        candidate = value.get("canonical_name")
        if not isinstance(candidate, str):
            raise TypeError("normalized record requires a string canonical_name")
        normalized = normalize_ingredient(candidate)
        raw = raw if isinstance(raw, str) else candidate
    else:
        if not isinstance(value, str):
            raise TypeError("ingredient value must be a string or normalized record")
        raw = value
        normalized = normalize_ingredient(value)

    canonical_name = normalized["canonical_name"]
    if not canonical_name:
        return None

    knowledge = get_ingredient_knowledge(canonical_name)
    if knowledge is None:
        return _unknown_result(raw, canonical_name)

    profile = get_analysis_profile(knowledge["canonical_name"])
    if profile is None:
        return _unknown_result(raw, knowledge["canonical_name"])

    result = {
        "raw": raw,
        "canonical_name": knowledge["canonical_name"],
        "status": "known",
        "category": knowledge["category"],
        "function": profile["function"],
        "common_uses": list(knowledge["common_uses"]),
        "consumer_summary": profile["consumer_summary"],
        "potential_concerns": copy.deepcopy(profile["potential_concerns"]),
        "concern_level": profile["concern_level"],
        "evidence_status": EVIDENCE_STATUS,
        "confidence": 0.9,
        "requires_review": profile["concern_level"] == "unknown",
    }
    return result


def analyze_ingredients(values: List[Union[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """Analyze multiple ingredients while preserving input order."""
    if not isinstance(values, list):
        raise TypeError("ingredient values must be a list")
    ingredients = [analyze_ingredient(value) for value in values]
    ingredients = [result for result in ingredients if result is not None]
    known = sum(result["status"] == "known" for result in ingredients)
    unknown = len(ingredients) - known
    return {
        "ingredients": ingredients,
        "summary": {
            "total": len(ingredients),
            "known": known,
            "unknown": unknown,
            "requires_review": sum(result["requires_review"] for result in ingredients),
        },
    }


__all__ = ["analyze_ingredient", "analyze_ingredients", "get_analysis_profile"]
