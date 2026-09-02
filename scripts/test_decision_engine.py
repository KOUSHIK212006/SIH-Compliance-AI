"""Behavior tests for evidence-backed product assessment."""
from src.compliance import load_development_rules
from src.decision import assess_product
from src.pipeline import PipelineConfig, run_product_pipeline
from src.regulatory import load_demo_evidence


def _report(text, **kwargs):
    return run_product_pipeline(ocr_text=text, **kwargs)


def _run_tests():
    clean = assess_product(_report("Ingredients: cocoa butter"))
    assert clean["overall_status"] == "REVIEW"
    assert clean["ingredient_assessments"][0]["normalized_name"] == "cocoa butter"
    assert clean["compliance_findings"] == []
    assert clean["evidence"] == []
    assert any("evidence" in item.lower() for item in clean["uncertainty"])

    sugar = assess_product(_report("Ingredients: sugar"))
    assert sugar["ingredient_assessments"][0]["category"] == "sweetener"
    assert sugar["ingredient_assessments"][0]["function"] == "sweetening"
    assert sugar["ingredient_assessments"][0]["additive_code"] is None

    additive = assess_product(_report("Ingredients: citric acid, E330"))
    additive_names = [item["normalized_name"] for item in additive["ingredient_assessments"]]
    assert additive_names == ["citric acid", "E330"]
    assert additive["ingredient_assessments"][1]["additive_code"] == "E330"

    unknown = assess_product(_report("Ingredients: sugar, unknown ingredient"))
    unknown_assessment = unknown["ingredient_assessments"][1]
    assert unknown_assessment["status"] == "review"
    assert unknown_assessment["confidence"] == 0.1
    assert unknown["overall_status"] == "REVIEW"
    assert unknown["summary"] if "summary" in unknown else True

    rules = load_development_rules()
    for rule in rules:
        if rule["rule_id"] == "DEV-RESTRICTED-INGREDIENT":
            rule["target"]["restricted_ingredients"] = ["sugar"]
    mixed_report = _report("Ingredients: Sugar, Sugar, Unknown Ingredient", rules=rules)
    mixed = assess_product(mixed_report)
    finding_ids = {finding["rule_id"] for finding in mixed["compliance_findings"]}
    assert {"DEV-RESTRICTED-INGREDIENT", "DEV-DUPLICATE-INGREDIENT", "DEV-UNKNOWN-INGREDIENT"}.issubset(finding_ids)
    assert len(mixed["compliance_findings"]) >= 3
    assert mixed["overall_status"] == "ATTENTION"
    assert mixed["uncertainty"]

    demo_report = _report(
        "Ingredients: demo additive",
        config=PipelineConfig(regulatory_evidence_enabled=True),
        regulatory_evidence_store=load_demo_evidence(),
    )
    with_evidence = assess_product(demo_report)
    assert with_evidence["evidence"]
    assert with_evidence["evidence"][0]["sources"][0]["document_id"] == "TEST-DOC-001"
    assert with_evidence["ingredient_assessments"][0]["evidence"]
    assert with_evidence["ingredient_assessments"][0]["evidence"][0]["authority"] == "TEST AUTHORITY"

    empty = assess_product(_report("Ingredients:"))
    assert empty["overall_status"] == "REVIEW"
    assert empty["ingredient_assessments"] == []
    assert empty["confidence"] is None
    assert empty["uncertainty"]

    for result in (clean, sugar, additive, unknown, mixed, with_evidence, empty):
        if result["confidence"] is not None:
            assert 0.0 <= result["confidence"] <= 1.0
        if result["overall_score"] is not None:
            assert 0.0 <= result["overall_score"] <= 1.0
        assert "medical" not in result["status_reason"].lower()
        assert "diagnosis" not in str(result).lower()
        for item in result["ingredient_assessments"]:
            if item["confidence"] is not None:
                assert 0.0 <= item["confidence"] <= 1.0

    first = assess_product(_report("Ingredients: sugar, unknown ingredient"))
    second = assess_product(_report("Ingredients: sugar, unknown ingredient"))
    assert first == second

    print("All decision engine tests passed.")


if __name__ == "__main__":
    _run_tests()
