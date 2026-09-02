"""Deterministic explanation generation for existing pipeline decisions."""
from typing import Any, Dict, List, Optional

from .evidence import get_evidence_for_ingredient
from .models import ExplainableFinding, ReasoningStep


def _matching_findings(analysis: Dict[str, Any], rule_result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(rule_result, dict):
        return []
    canonical = analysis.get("canonical_name", "")
    raw = analysis.get("raw", canonical)
    matches = []
    for finding in rule_result.get("findings", []):
        if not isinstance(finding, dict):
            continue
        ingredient = finding.get("ingredient")
        if ingredient is None or str(ingredient).casefold() in {str(canonical).casefold(), str(raw).casefold()}:
            matches.append(finding)
    return matches


def explain_ingredient_analysis(
    analysis: Dict[str, Any],
    rule_result: Optional[Dict[str, Any]] = None,
    input_ingredient: Optional[str] = None,
) -> Dict[str, Any]:
    """Explain one existing analyzer result without making new decisions.

    ``analysis`` should come from ``analyze_ingredient``. Optional
    ``rule_result`` should come from the existing rule engine. The function
    only reports applicable findings and analyzer output; it does not evaluate
    compliance independently.
    """
    if not isinstance(analysis, dict):
        raise TypeError("analysis must be a dictionary")

    normalized_name = analysis.get("canonical_name")
    if not isinstance(normalized_name, str) or not normalized_name:
        raise ValueError("analysis must contain a non-empty canonical_name")

    ingredient = input_ingredient if isinstance(input_ingredient, str) else analysis.get("raw", normalized_name)
    if not isinstance(ingredient, str):
        ingredient = normalized_name

    rule_findings = _matching_findings(analysis, rule_result)
    rule_ids = [str(finding["rule_id"]) for finding in rule_findings if finding.get("rule_id")]
    severity = rule_findings[0].get("severity") if rule_findings else None
    evidence_result = get_evidence_for_ingredient(normalized_name)

    status = analysis.get("status", "unknown")
    concern_level = analysis.get("concern_level", "unknown")
    category = analysis.get("category")
    function = analysis.get("function")
    if rule_findings:
        technical_reason = "The existing rule engine produced applicable finding(s): " + ", ".join(rule_ids) + "."
        consumer_explanation = "The system flagged this ingredient under the current development rule set; this is not a verified regulatory conclusion."
    elif status == "known":
        technical_reason = "The ingredient matched the existing knowledge base and ingredient analysis profile."
        consumer_explanation = f"This ingredient is identified as {function or category or 'a known ingredient'} in the current development data."
    else:
        technical_reason = "The analyzer could not match the ingredient to a complete local knowledge profile."
        consumer_explanation = "The ingredient could not be fully identified in the current development data, so further review is recommended."

    uncertainty = []
    if not evidence_result["evidence_available"]:
        uncertainty.append("No verified evidence source is available in the current knowledge base.")
    if status != "known":
        uncertainty.append("Ingredient identity or profile information is incomplete.")
    if not rule_findings:
        uncertainty.append("No applicable rule-engine finding was supplied for this ingredient.")
    uncertainty.append("Ingredient quantity and product context were not supplied.")

    steps = [
        ReasoningStep("input", "The ingredient value was supplied to the existing analysis pipeline.", ingredient, ingredient),
        ReasoningStep("normalization", "The analyzer supplied this normalized ingredient name.", ingredient, normalized_name),
        ReasoningStep("knowledge_lookup", "The knowledge base supplied the available category and function.", normalized_name, {"category": category, "function": function}),
        ReasoningStep("rule_evaluation", "The existing rule-engine output was inspected; no new regulatory decision was made.", rule_result or {}, rule_findings),
        ReasoningStep("analysis", "The existing ingredient analyzer supplied the consumer analysis status and concern level.", analysis, {"status": status, "concern_level": concern_level}),
    ]

    finding = ExplainableFinding(
        ingredient=ingredient,
        normalized_name=normalized_name,
        category=category,
        function=function,
        status="review" if analysis.get("requires_review") or rule_findings else status,
        severity=severity,
        confidence=analysis.get("confidence") if isinstance(analysis.get("confidence"), (int, float)) else None,
        technical_reason=technical_reason,
        consumer_explanation=consumer_explanation,
        reasoning_steps=steps,
        evidence=[],
        evidence_available=evidence_result["evidence_available"],
        uncertainty=uncertainty,
        recommendation="Human review is recommended because the current data is development-only or incomplete." if uncertainty else "No additional review is indicated by the supplied analysis.",
        rule_ids=rule_ids,
        knowledge_source_id=evidence_result.get("knowledge_source_id"),
    )
    return finding.to_dict()


__all__ = ["explain_ingredient_analysis"]
