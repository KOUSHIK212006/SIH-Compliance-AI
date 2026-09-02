"""Behavior tests for the deterministic consumer ingredient analyzer."""
from src.ingredients import normalize_ingredient
from src.analysis import analyze_ingredient, analyze_ingredients, get_analysis_profile


def _run_tests():
    known = analyze_ingredient("sodium benzoate")
    assert known is not None
    assert known["status"] == "known"
    assert known["canonical_name"] == "sodium benzoate"
    assert known["category"] == "preservative"
    assert known["function"] == "preservation"
    assert known["evidence_status"] == "development_demo"

    assert analyze_ingredient("  SODIUM   BENZOATE  ")["canonical_name"] == "sodium benzoate"
    normalized = normalize_ingredient("  Milk   Powder ")
    normalized_result = analyze_ingredient(normalized)
    assert normalized_result["canonical_name"] == "milk powder"
    assert normalized_result["raw"] == "  Milk   Powder "

    unknown = analyze_ingredient("unlisted ingredient")
    assert unknown["status"] == "unknown"
    assert unknown["requires_review"] is True
    assert unknown["confidence"] < 0.5

    multi = analyze_ingredients(["sugar", "unknown ingredient", "SALT"])
    assert [item["canonical_name"] for item in multi["ingredients"]] == ["sugar", "unknown ingredient", "salt"]
    assert multi["summary"] == {"total": 3, "known": 2, "unknown": 1, "requires_review": 1}

    for result in multi["ingredients"] + [known, unknown]:
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["concern_level"] in {"low", "moderate", "high", "unknown"}
        for concern in result["potential_concerns"]:
            assert {"topic", "explanation", "context", "evidence_status"}.issubset(concern)
            assert concern["evidence_status"] == "development_demo"
        assert "diagnosis" not in result
        assert "citation" not in result
        assert "url" not in result

    assert get_analysis_profile("SUGAR")["function"] == "sweetening"
    assert get_analysis_profile("unlisted ingredient") is None
    incomplete = analyze_ingredient("not in the local profiles")
    assert incomplete["requires_review"] is True
    assert incomplete["consumer_summary"] == "Insufficient information for a development analysis."

    first = analyze_ingredients(["sugar", "sodium benzoate", "unknown ingredient"])
    second = analyze_ingredients(["sugar", "sodium benzoate", "unknown ingredient"])
    assert first == second

    print("All ingredient analyzer tests passed.")


if __name__ == "__main__":
    _run_tests()
