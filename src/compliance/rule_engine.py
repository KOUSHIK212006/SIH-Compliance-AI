"""Deterministic development rule engine for ingredient evaluation.

The rules in this module are demonstrations only. They are not verified
regulatory requirements and must not be presented as legal conclusions.
"""
import copy
import re
from typing import Any, Dict, Iterable, List, Optional

from src.ingredients import get_ingredient_knowledge, normalize_ingredient


SOURCE_TYPE = "development_demo"
SUPPORTED_SEVERITIES = {"info", "warning", "critical"}
SUPPORTED_RULE_TYPES = {
    "restricted_ingredient",
    "mandatory_declaration",
    "duplicate_ingredient",
    "unknown_ingredient",
    "malformed_additive_code",
}
REQUIRED_RULE_FIELDS = {"rule_id", "name", "description", "rule_type", "target", "severity", "enabled", "source_type"}
_ADDITIVE_LIKE = re.compile(r"^\s*(?:e|ins)", re.IGNORECASE)
_VALID_ADDITIVE = re.compile(r"^\s*(?:e|ins)\s*-?\s*\d{2,3}\s*$", re.IGNORECASE)


def load_development_rules() -> List[Dict[str, Any]]:
    """Return the built-in deterministic rules labelled as development demos."""
    return [
        {
            "rule_id": "DEV-RESTRICTED-INGREDIENT",
            "name": "Configured restricted ingredient demo",
            "description": "Flags ingredients explicitly listed by the development configuration.",
            "rule_type": "restricted_ingredient",
            "target": {"restricted_ingredients": ["demo restricted ingredient"]},
            "severity": "warning",
            "enabled": True,
            "source_type": SOURCE_TYPE,
        },
        {
            "rule_id": "DEV-MANDATORY-DECLARATION",
            "name": "Configured declaration demo",
            "description": "Flags a missing configured declaration when a demo condition is present.",
            "rule_type": "mandatory_declaration",
            "target": {"when_ingredient": "milk powder", "required_declaration": "milk declaration"},
            "severity": "warning",
            "enabled": True,
            "source_type": SOURCE_TYPE,
        },
        {
            "rule_id": "DEV-DUPLICATE-INGREDIENT",
            "name": "Duplicate ingredient demo",
            "description": "Flags repeated canonical ingredient values in the supplied list.",
            "rule_type": "duplicate_ingredient",
            "target": "ingredient_list",
            "severity": "info",
            "enabled": True,
            "source_type": SOURCE_TYPE,
        },
        {
            "rule_id": "DEV-UNKNOWN-INGREDIENT",
            "name": "Unknown ingredient demo",
            "description": "Flags values not found in the local development knowledge base.",
            "rule_type": "unknown_ingredient",
            "target": "ingredient_knowledge_base",
            "severity": "warning",
            "enabled": True,
            "source_type": SOURCE_TYPE,
        },
        {
            "rule_id": "DEV-MALFORMED-ADDITIVE",
            "name": "Malformed additive code demo",
            "description": "Flags additive-looking values that do not match the configured code format.",
            "rule_type": "malformed_additive_code",
            "target": "additive_code",
            "severity": "warning",
            "enabled": True,
            "source_type": SOURCE_TYPE,
        },
    ]


def _finding(rule: Dict[str, Any], message: str, ingredient: Optional[str] = None) -> Dict[str, Any]:
    result = {
        "rule_id": rule["rule_id"],
        "severity": rule["severity"],
        "message": message,
        "source_type": rule["source_type"],
    }
    if ingredient is not None:
        result["ingredient"] = ingredient
    return result


def _validate_rules(rules: Iterable[Any]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    valid = []
    errors = []
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append({"index": index, "message": "rule must be a dictionary"})
            continue
        missing = sorted(REQUIRED_RULE_FIELDS - set(rule))
        if missing:
            errors.append({"index": index, "rule_id": rule.get("rule_id"), "message": f"missing rule fields: {', '.join(missing)}"})
            continue
        if rule["rule_type"] not in SUPPORTED_RULE_TYPES:
            errors.append({"index": index, "rule_id": rule["rule_id"], "message": f"unsupported rule type: {rule['rule_type']}"})
            continue
        if rule["severity"] not in SUPPORTED_SEVERITIES:
            errors.append({"index": index, "rule_id": rule["rule_id"], "message": f"unsupported severity: {rule['severity']}"})
            continue
        if not isinstance(rule["enabled"], bool):
            errors.append({"index": index, "rule_id": rule["rule_id"], "message": "enabled must be boolean"})
            continue
        if rule["source_type"] != SOURCE_TYPE:
            errors.append({"index": index, "rule_id": rule["rule_id"], "message": "rule source_type must be development_demo"})
            continue
        valid.append(rule)
    return valid, errors


def _canonical_inputs(ingredients: Any) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not isinstance(ingredients, list):
        return [], [{"message": "ingredients must be a list"}]
    normalized = []
    errors = []
    for index, item in enumerate(ingredients):
        try:
            if isinstance(item, dict):
                value = item.get("canonical_name") or item.get("name")
                if not isinstance(value, str):
                    raise TypeError("record requires a string canonical_name or name")
                record = normalize_ingredient(value)
                record["raw"] = item.get("raw", value)
            else:
                record = normalize_ingredient(item)
            if record["ingredient_type"] == "invalid":
                raise ValueError("ingredient value is empty")
            normalized.append(record)
        except (TypeError, ValueError) as exc:
            errors.append({"index": index, "message": str(exc)})
    return normalized, errors


def _evaluate(ingredients: Any, rules: Optional[List[Dict[str, Any]]] = None, declarations: Optional[List[str]] = None) -> Dict[str, Any]:
    records, errors = _canonical_inputs(ingredients)
    selected_rules = load_development_rules() if rules is None else rules
    if not isinstance(selected_rules, list):
        errors.append({"message": "rules must be a list"})
        selected_rules = []
    valid_rules, rule_errors = _validate_rules(selected_rules)
    errors.extend({"type": "invalid_rule", **error} for error in rule_errors)

    findings = []
    passed_rules = []
    failed_rules = []
    canonical_names = [record["canonical_name"] for record in records]

    for rule in valid_rules:
        if not rule["enabled"]:
            continue
        rule_findings = []
        rule_type = rule["rule_type"]
        if rule_type == "restricted_ingredient":
            restricted = {str(value).casefold() for value in rule["target"].get("restricted_ingredients", [])} if isinstance(rule["target"], dict) else set()
            rule_findings = [_finding(rule, "Development rule triggered for a configured restricted ingredient.", name) for name in canonical_names if name.casefold() in restricted]
        elif rule_type == "unknown_ingredient":
            rule_findings = [_finding(rule, "Development rule triggered: ingredient is not in the local knowledge base.", name) for name in canonical_names if get_ingredient_knowledge(name) is None]
        elif rule_type == "duplicate_ingredient":
            seen = set()
            duplicates = []
            for name in canonical_names:
                if name in seen and name not in duplicates:
                    duplicates.append(name)
                seen.add(name)
            rule_findings = [_finding(rule, "Development rule triggered: duplicate ingredient detected.", name) for name in duplicates]
        elif rule_type == "malformed_additive_code":
            rule_findings = [_finding(rule, "Development rule triggered: malformed additive code.", record["raw"]) for record in records if isinstance(record.get("raw"), str) and _ADDITIVE_LIKE.match(record["raw"]) and not _VALID_ADDITIVE.fullmatch(record["raw"])]
        elif rule_type == "mandatory_declaration" and isinstance(rule["target"], dict):
            condition = str(rule["target"].get("when_ingredient", "")).casefold()
            required = str(rule["target"].get("required_declaration", ""))
            provided = {str(value).casefold() for value in (declarations or [])}
            if condition and required and condition in {name.casefold() for name in canonical_names} and required.casefold() not in provided:
                rule_findings = [_finding(rule, "Development rule triggered: configured declaration is missing.", condition)]

        if rule_findings:
            findings.extend(rule_findings)
            failed_rules.append(rule["rule_id"])
        else:
            passed_rules.append(rule["rule_id"])

    return {
        "status": "review_required" if findings or errors else "passed",
        "findings": findings,
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "review_required": bool(findings or errors),
        "errors": errors,
    }


def evaluate_ingredients(ingredients: Any, rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Evaluate simple names or normalized ingredient records deterministically."""
    return _evaluate(ingredients, rules)


def evaluate_product(product_data: Dict[str, Any], rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Evaluate a product dictionary containing ``ingredients`` and declarations."""
    if not isinstance(product_data, dict):
        return _evaluate(None, rules)
    return _evaluate(product_data.get("ingredients", []), rules, product_data.get("declarations", []))


__all__ = ["evaluate_ingredients", "evaluate_product", "load_development_rules"]
