"""Behavior tests for the deterministic XAI and evidence layer."""
from src.analysis import analyze_ingredient
from src.compliance import evaluate_ingredients
from src.xai import explain_ingredient_analysis, get_evidence_for_ingredient


def _run_tests():
    analysis = analyze_ingredient("  SODIUM   BENZOATE ")
    rule_result = evaluate_ingredients(["sodium benzoate"])
    explanation = explain_ingredient_analysis(analysis, rule_result, input_ingredient="  SODIUM   BENZOATE ")

    assert explanation["ingredient"] == "  SODIUM   BENZOATE "
    assert explanation["normalized_name"] == "sodium benzoate"
    assert explanation["category"] == "preservative"
    assert explanation["function"] == "preservation"
    assert explanation["reasoning_steps"]
    assert explanation["technical_reason"]
    assert explanation["consumer_explanation"]
    assert explanation["uncertainty"]
    assert 0.0 <= explanation["confidence"] <= 1.0
    assert explanation["evidence"] == []
    assert explanation["evidence_available"] is False
    assert explanation["knowledge_source_id"] == "local-kb:sodium benzoate"

    unknown = explain_ingredient_analysis(analyze_ingredient("unlisted ingredient"))
    assert unknown["status"] == "review"
    assert unknown["evidence_available"] is False
    assert unknown["uncertainty"]
    assert unknown["requires_review"] if "requires_review" in unknown else True

    restricted_rules = evaluate_ingredients(["sugar"])
    custom = restricted_rules
    custom["findings"] = [{
        "rule_id": "DEV-EXAMPLE-001",
        "severity": "warning",
        "ingredient": "sugar",
        "message": "Development rule triggered for demonstration.",
        "source_type": "development_demo",
    }]
    flagged = explain_ingredient_analysis(analyze_ingredient("sugar"), custom)
    assert flagged["rule_ids"] == ["DEV-EXAMPLE-001"]
    assert flagged["severity"] == "warning"
    assert flagged["status"] == "review"
    assert "DEV-EXAMPLE-001" in flagged["technical_reason"]

    evidence = get_evidence_for_ingredient("citric acid")
    assert evidence["evidence_available"] is False
    assert evidence["evidence"] == []
    assert "unavailable_reason" in evidence
    assert "citation" not in evidence
    assert "url" not in evidence

    assert "diagnosis" not in explanation
    assert "medical_advice" not in explanation
    assert "guaranteed" not in explanation["consumer_explanation"].lower()
    assert "verified regulatory" not in explanation["consumer_explanation"].lower()

    assert explanation == explain_ingredient_analysis(analysis, rule_result, input_ingredient="  SODIUM   BENZOATE ")

    print("All XAI tests passed.")


if __name__ == "__main__":
    _run_tests()
