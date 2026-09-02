"""Small deterministic local knowledge base for ingredients and additives."""
import copy
import re
from typing import Dict, List, Optional, Any


SOURCE_TYPE = "local_development_knowledge_base"
_CODE_PATTERN = re.compile(r"^(E|INS)\s*-?\s*(\d{2,3})$", re.IGNORECASE)


def _entry(
    canonical_name: str,
    ingredient_type: str,
    category: str,
    description: str,
    common_uses: List[str],
    aliases: List[str],
    additive_code: Optional[str] = None,
    additive_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build one immutable-by-convention dataset record."""
    return {
        "canonical_name": canonical_name,
        "ingredient_type": ingredient_type,
        "category": category,
        "description": description,
        "common_uses": common_uses,
        "additive_code": additive_code,
        "additive_codes": additive_codes or ([additive_code] if additive_code else []),
        "aliases": aliases,
        "source_type": SOURCE_TYPE,
    }


_KNOWLEDGE_ENTRIES = [
    _entry("sugar", "ingredient", "sweetener", "A sweet crystalline food ingredient.", ["sweetening"], ["sugar"]),
    _entry("salt", "ingredient", "mineral salt", "A crystalline ingredient used to season food.", ["seasoning"], ["salt", "sodium chloride"]),
    _entry(
        "citric acid", "ingredient", "acidulant",
        "An organic acid commonly used to provide acidity and flavor.",
        ["acidity regulator", "flavoring"], ["citric acid"], "E330", ["E330", "INS330"],
    ),
    _entry(
        "sodium benzoate", "ingredient", "preservative",
        "A sodium salt used as a food preservative.",
        ["preservation"], ["sodium benzoate"], "E211", ["E211", "INS211"],
    ),
    _entry(
        "ascorbic acid", "ingredient", "antioxidant",
        "An ingredient used to help protect food quality during storage.",
        ["antioxidant", "flour treatment"], ["ascorbic acid", "vitamin c"], "E300", ["E300", "INS300"],
    ),
    _entry("milk powder", "ingredient", "dairy ingredient", "Dried milk used as a food ingredient.", ["dairy solids", "texture"], ["milk powder", "dried milk"]),
    _entry("cocoa butter", "ingredient", "cocoa ingredient", "The fat obtained from cocoa beans.", ["confectionery texture", "fat ingredient"], ["cocoa butter"]),
]


def _clean_lookup_value(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("ingredient lookup value must be a string")
    return re.sub(r"\s+", " ", value.strip())


def _canonical_code(value: str) -> Optional[str]:
    match = _CODE_PATTERN.fullmatch(value)
    if not match:
        return None
    return f"{match.group(1).upper()}{match.group(2)}"


def _record_for_lookup(entry: Dict[str, Any], lookup_input: str) -> Dict[str, Any]:
    record = copy.deepcopy(entry)
    record["lookup_input"] = lookup_input
    return record


def get_ingredient_knowledge(value: str) -> Optional[Dict[str, Any]]:
    """Return local knowledge for a canonical name, alias, or explicit code.

    Lookup is case-insensitive and collapses repeated whitespace. Unknown or
    blank values return ``None``. Only codes explicitly listed on an entry
    are accepted; no E-code/INS-code equivalence is inferred automatically.
    """
    cleaned = _clean_lookup_value(value)
    if not cleaned:
        return None

    code = _canonical_code(cleaned)
    normalized_name = cleaned.casefold()
    for entry in _KNOWLEDGE_ENTRIES:
        names = {entry["canonical_name"].casefold(), *(alias.casefold() for alias in entry["aliases"])}
        codes = set(entry["additive_codes"])
        if (code and code in codes) or (not code and normalized_name in names):
            return _record_for_lookup(entry, value)
    return None


def lookup_ingredient(value: str) -> Optional[Dict[str, Any]]:
    """Compatibility alias for :func:`get_ingredient_knowledge`."""
    return get_ingredient_knowledge(value)


def list_ingredient_knowledge() -> List[Dict[str, Any]]:
    """Return copies of all local knowledge entries in deterministic order."""
    return [copy.deepcopy(entry) for entry in _KNOWLEDGE_ENTRIES]


__all__ = ["get_ingredient_knowledge", "lookup_ingredient", "list_ingredient_knowledge"]
