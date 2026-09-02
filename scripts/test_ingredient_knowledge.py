"""Tests for the local ingredient knowledge base."""
from src.ingredients import (
    get_ingredient_knowledge,
    lookup_ingredient,
    list_ingredient_knowledge,
)


def _run_tests():
    sugar = get_ingredient_knowledge("sugar")
    assert sugar is not None
    assert sugar["canonical_name"] == "sugar"

    assert get_ingredient_knowledge("  SUGAR  ") == get_ingredient_knowledge("sugar") | {"lookup_input": "  SUGAR  "}

    alias = get_ingredient_knowledge("sodium chloride")
    assert alias is not None and alias["canonical_name"] == "salt"

    for code in ("E330", "INS330", "INS 330", "INS-330", "e330"):
        result = get_ingredient_knowledge(code)
        assert result is not None, f"Expected explicit code lookup to resolve: {code}"
        assert result["canonical_name"] == "citric acid"
        assert result["additive_code"] == "E330"

    assert lookup_ingredient("milk powder")["canonical_name"] == "milk powder"
    assert get_ingredient_knowledge("unknown ingredient") is None
    assert get_ingredient_knowledge("   ") is None

    record = get_ingredient_knowledge("Citric Acid")
    assert record is not None
    expected_keys = {
        "lookup_input", "canonical_name", "ingredient_type", "category",
        "description", "common_uses", "additive_code", "additive_codes",
        "aliases", "source_type",
    }
    assert expected_keys.issubset(record.keys())
    assert record["lookup_input"] == "Citric Acid"
    assert record["canonical_name"] == "citric acid"
    assert "health" not in record
    assert "compliance" not in record
    assert record["source_type"] == "local_development_knowledge_base"

    entries = list_ingredient_knowledge()
    assert len(entries) >= 7
    assert [entry["canonical_name"] for entry in entries] == [
        "sugar", "salt", "citric acid", "sodium benzoate",
        "ascorbic acid", "milk powder", "cocoa butter",
    ]

    print("All ingredient knowledge tests passed.")


if __name__ == "__main__":
    _run_tests()
