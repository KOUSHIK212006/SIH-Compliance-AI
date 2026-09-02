"""Tests for the reusable ingredient normalizer."""
from src.ingredients import normalize_ingredient, normalize_ingredients


def _run_tests():
    cases = [
        ("sugar", "sugar", "ingredient"),
        ("Sugar", "sugar", "ingredient"),
        ("SUGAR", "sugar", "ingredient"),
        ("  Sugar  ", "sugar", "ingredient"),
        ("MILK   POWDER", "milk powder", "ingredient"),
        ("cocoa butter", "cocoa butter", "ingredient"),
        ("whey   protein concentrate", "whey protein concentrate", "ingredient"),
        ("E330", "E330", "additive_code"),
        ("e330", "E330", "additive_code"),
        ("INS 330", "INS330", "additive_code"),
        ("INS-330", "INS330", "additive_code"),
        ("ins330", "INS330", "additive_code"),
    ]

    for raw, canonical_name, ingredient_type in cases:
        result = normalize_ingredient(raw)
        assert result["raw"] == raw
        assert result["canonical_name"] == canonical_name
        assert result["ingredient_type"] == ingredient_type
        expected_code = canonical_name if ingredient_type == "additive_code" else None
        assert result["additive_code"] == expected_code

    empty = normalize_ingredient(" \t\n ")
    assert empty == {
        "raw": " \t\n ",
        "canonical_name": "",
        "ingredient_type": "invalid",
        "additive_code": None,
    }

    values = ["Sugar", " milk   powder ", "SUGAR", "INS-330", "sugar"]
    results = normalize_ingredients(values)
    assert [result["canonical_name"] for result in results] == [
        "sugar", "milk powder", "sugar", "INS330", "sugar"
    ]
    assert [result["raw"] for result in results] == values
    assert results[0] != results[2]
    assert results[0]["canonical_name"] == results[2]["canonical_name"]

    print("All ingredient normalizer tests passed.")


if __name__ == "__main__":
    _run_tests()
