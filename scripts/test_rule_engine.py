"""Behavior tests for the deterministic development rule engine."""
from src.compliance import evaluate_ingredients, evaluate_product, load_development_rules


def _run_tests():
    rules = load_development_rules()
    assert rules
    assert all(rule["source_type"] == "development_demo" for rule in rules)
    assert all(rule["severity"] in {"info", "warning", "critical"} for rule in rules)

    empty = evaluate_ingredients([])
    assert empty["findings"] == []
    assert empty["review_required"] is False
    assert empty["status"] == "passed"

    known = evaluate_ingredients(["sugar", "salt"], rules)
    assert known["findings"] == []
    assert "DEV-UNKNOWN-INGREDIENT" in known["passed_rules"]

    unknown = evaluate_ingredients(["sugar", "mystery ingredient"], rules)
    unknown_findings = [finding for finding in unknown["findings"] if finding["rule_id"] == "DEV-UNKNOWN-INGREDIENT"]
    assert len(unknown_findings) == 1
    assert unknown_findings[0]["ingredient"] == "mystery ingredient"

    duplicate = evaluate_ingredients(["Sugar", "sugar"], rules)
    duplicate_findings = [finding for finding in duplicate["findings"] if finding["rule_id"] == "DEV-DUPLICATE-INGREDIENT"]
    assert len(duplicate_findings) == 1
    assert duplicate_findings[0]["ingredient"] == "sugar"

    restricted_rule = [rule for rule in rules if rule["rule_id"] == "DEV-RESTRICTED-INGREDIENT"][0]
    restricted_rule["target"]["restricted_ingredients"] = ["sugar"]
    restricted = evaluate_ingredients(["sugar"], rules)
    restricted_findings = [finding for finding in restricted["findings"] if finding["rule_id"] == "DEV-RESTRICTED-INGREDIENT"]
    assert len(restricted_findings) == 1

    multiple = evaluate_product({"ingredients": ["sugar", "sugar", "mystery ingredient"]}, rules)
    assert len(multiple["findings"]) >= 2
    assert multiple["review_required"] is True
    for finding in multiple["findings"]:
        assert finding["rule_id"]
        assert finding["source_type"] == "development_demo"
        assert finding["severity"] in {"info", "warning", "critical"}

    declaration = evaluate_product({"ingredients": ["milk powder"], "declarations": []}, rules)
    assert any(f["rule_id"] == "DEV-MANDATORY-DECLARATION" for f in declaration["findings"])

    malformed_rules = [{"rule_id": "DEV-BAD", "name": "bad"}]
    invalid = evaluate_ingredients(["sugar"], malformed_rules)
    assert invalid["review_required"] is True
    assert invalid["errors"]
    assert invalid["errors"][0]["type"] == "invalid_rule"

    unsupported = dict(rules[0])
    unsupported["rule_type"] = "unsupported_demo_type"
    invalid_type = evaluate_ingredients([], [unsupported])
    assert invalid_type["errors"]
    assert "unsupported rule type" in invalid_type["errors"][0]["message"]

    assert not any("health" in key.lower() or "medical" in key.lower() for key in multiple)
    assert not any("compliance conclusion" in finding["message"].lower() for finding in multiple["findings"])

    first = evaluate_ingredients(["salt", "mystery ingredient", "salt"], rules)
    second = evaluate_ingredients(["salt", "mystery ingredient", "salt"], rules)
    assert first == second

    print("All rule engine tests passed.")


if __name__ == "__main__":
    _run_tests()
