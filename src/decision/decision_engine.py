"""Deterministic aggregation of existing SIH pipeline outputs."""
from typing import Any, Dict, List, Optional

from .models import IngredientAssessment, ProductAssessment


_SEVERITY_RANK = {"info": 1, "warning": 2, "critical": 3}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _find_analysis(analyses: List[Dict[str, Any]], canonical_name: str) -> Dict[str, Any]:
    for analysis in analyses:
        if isinstance(analysis, dict) and analysis.get("canonical_name") == canonical_name:
            return analysis
    return {}


def _findings_for(findings: List[Dict[str, Any]], canonical_name: str, raw: str) -> List[Dict[str, Any]]:
    matches = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        target = finding.get("ingredient")
        if target is None or str(target).casefold() in {canonical_name.casefold(), raw.casefold()}:
            matches.append(finding)
    return matches


def _evidence_for(evidence: List[Dict[str, Any]], canonical_name: str) -> List[Dict[str, Any]]:
    matches = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        if item.get("ingredient", "").casefold() == canonical_name.casefold():
            sources = item.get("sources")
            matches.extend(source for source in sources if isinstance(source, dict)) if isinstance(sources, list) else matches.append(item)
        elif item.get("canonical_name", "").casefold() == canonical_name.casefold():
            matches.append(item)
        elif item.get("chunk", {}).get("metadata", {}).get("ingredient", "").casefold() == canonical_name.casefold():
            matches.append(item)
    return matches


def _status(compliance: List[Dict[str, Any]], health: List[Dict[str, Any]], unknown: bool, requires_review: bool, errors: List[Dict[str, Any]]) -> tuple[str, str]:
    max_severity = max((_SEVERITY_RANK.get(item.get("severity"), 0) for item in compliance), default=0)
    concern_levels = {item.get("concern_level") for item in health}
    if max_severity >= _SEVERITY_RANK["critical"] or "high" in concern_levels:
        return "HIGH_CONCERN", "A critical compliance finding or high concern level was supplied by an existing module."
    unknown_only = bool(compliance) and all(item.get("rule_id") == "DEV-UNKNOWN-INGREDIENT" for item in compliance)
    if unknown and (not compliance or unknown_only):
        return "REVIEW", "Ingredient identity or supporting information was not sufficiently established by the existing pipeline."
    if max_severity >= _SEVERITY_RANK["warning"] or "moderate" in concern_levels:
        return "ATTENTION", "A warning-level compliance finding or moderate concern level was supplied by an existing module."
    if unknown or requires_review or errors:
        return "REVIEW", "The existing pipeline reported unknown, incomplete, or errored information requiring review."
    return "CLEAR", "No supplied compliance finding or supported concern required additional attention."


def assess_product(product_report: Dict[str, Any]) -> Dict[str, Any]:
    """Build an evidence-backed assessment from an existing pipeline report.

    This function does not perform OCR, normalization, rule evaluation, RAG,
    or independent health/compliance reasoning. ``overall_score`` is a
    transparent informational index based only on supplied finding severity;
    it is not a safety probability or legal-compliance score.
    """
    if not isinstance(product_report, dict):
        raise TypeError("product_report must be a dictionary")

    ingredient_section = product_report.get("ingredients", {})
    normalized = _as_list(ingredient_section.get("normalized")) if isinstance(ingredient_section, dict) else []
    analyses_section = product_report.get("analysis", {})
    analyses = _as_list(analyses_section.get("ingredient_results")) if isinstance(analyses_section, dict) else []
    compliance_section = product_report.get("compliance", {})
    compliance_findings = _as_list(compliance_section.get("findings")) if isinstance(compliance_section, dict) else []
    evidence = _as_list(product_report.get("evidence"))
    explanations = _as_list(product_report.get("explanations"))
    errors = _as_list(product_report.get("errors"))
    ingredient_assessments = []
    all_health = []
    uncertainties = []
    confidence_values = []
    unknown_found = False

    for record in normalized:
        if not isinstance(record, dict):
            errors.append({"stage": "decision", "message": "invalid normalized ingredient record"})
            continue
        canonical = record.get("canonical_name")
        if not isinstance(canonical, str) or not canonical:
            errors.append({"stage": "decision", "message": "normalized ingredient has no canonical_name"})
            continue
        raw = record.get("raw", canonical)
        analysis = _find_analysis(analyses, canonical)
        if analysis.get("status") == "unknown":
            unknown_found = True
        rules = _findings_for(compliance_findings, canonical, str(raw))
        health = _as_list(analysis.get("potential_concerns"))
        ingredient_evidence = _evidence_for(evidence, canonical)
        explanation = next((item for item in explanations if isinstance(item, dict) and item.get("normalized_name") == canonical), None)
        uncertainty = []
        if analysis.get("status") != "known":
            uncertainty.append("Ingredient knowledge is unavailable or incomplete.")
        if analysis.get("requires_review"):
            uncertainty.append("The existing ingredient analyzer recommended review.")
        if not ingredient_evidence:
            uncertainty.append("No supporting evidence was supplied for this ingredient.")
        if not rules:
            uncertainty.append("No applicable compliance finding was supplied for this ingredient.")
        if isinstance(analysis.get("confidence"), (int, float)):
            confidence_values.append(float(analysis["confidence"]))
        if uncertainty:
            uncertainties.extend(f"{canonical}: {item}" for item in uncertainty)
        all_health.extend(health)
        ingredient_assessments.append(IngredientAssessment(
            ingredient=str(raw), normalized_name=canonical,
            category=analysis.get("category"), function=analysis.get("function"),
            additive_code=record.get("additive_code"), rule_results=rules,
            health_findings=health, evidence=ingredient_evidence,
            xai_explanation=explanation, confidence=analysis.get("confidence"),
            uncertainty=uncertainty,
            status="review" if analysis.get("requires_review") or rules else analysis.get("status", "unknown"),
        ))

    unknown = unknown_found
    requires_review = bool(product_report.get("summary", {}).get("requires_review")) or any(item.uncertainty for item in ingredient_assessments)
    overall_status, reason = _status(compliance_findings, all_health, unknown, requires_review, errors)
    max_severity = max((_SEVERITY_RANK.get(item.get("severity"), 0) for item in compliance_findings), default=0)
    overall_score = round(max(0.0, 1.0 - (max_severity / 3.0)), 3)
    if not ingredient_assessments:
        overall_score = None
        uncertainties.append("No ingredient assessments were supplied.")
        overall_status = "REVIEW"
        reason = "No ingredient assessments were supplied by the existing pipeline."
    recommendations = []
    if overall_status != "CLEAR":
        recommendations.append("Review the flagged ingredients, source evidence, and product context before drawing conclusions.")
    if not evidence:
        recommendations.append("Obtain verified source evidence before treating this assessment as regulatory guidance.")
    if not recommendations:
        recommendations.append("No additional review was indicated by the supplied development outputs.")
    confidence = round(sum(confidence_values) / len(confidence_values), 3) if confidence_values else None
    return ProductAssessment(
        product_name=product_report.get("product", {}).get("product_name") if isinstance(product_report.get("product"), dict) else None,
        ingredients=normalized, overall_status=overall_status, overall_score=overall_score,
        ingredient_assessments=ingredient_assessments, compliance_findings=compliance_findings,
        health_findings=all_health, evidence=evidence, explanations=explanations,
        confidence=confidence, uncertainty=sorted(set(uncertainties)), recommendations=recommendations,
        status_reason=reason, errors=errors,
    ).to_dict()


__all__ = ["assess_product"]
