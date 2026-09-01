"""Tests for the reusable ingredient parser in src.ingredients."""

from src.ingredients import parse_ingredients


def _run_tests():
    samples = [
        (
            "Ingredients: Sugar, Wheat Flour (Wheat, Barley), Water, Salt, E330",
            {
                "expected_names": ["Sugar", "Wheat Flour", "Water", "Salt"],
                "expect_sub": {"Wheat Flour": ["Wheat", "Barley"]},
                "expect_additives": ["E330"],
            },
        ),
        (
            "Ingredients: MILK (skim MILK POWDER), SUGAR, INS 110, natural flavour (vanilla)",
            {
                "expected_names": ["MILK", "SUGAR", "natural flavour"],
                "expect_sub": {"MILK": ["skim MILK POWDER"], "natural flavour": ["vanilla"]},
                "expect_additives": ["INS110"],
            },
        ),
        (
            "Ingredients: tomato paste (tomatoes, salt), sugar, vegetable oils (palm, rapeseed), E100, E200",
            {
                "expected_names": ["tomato paste", "sugar", "vegetable oils"],
                "expect_sub": {"tomato paste": ["tomatoes", "salt"], "vegetable oils": ["palm", "rapeseed"]},
                "expect_additives": ["E100", "E200"],
            },
        ),
        (
            "I n g r e d i e n t s : s u g a r , w a t e r , s a l t",
            {
                "expected_names": ["sugar", "water", "salt"],
                "expect_sub": {},
                "expect_additives": [],
            },
        ),
        (
            "Ingredients: Flour (Wheat (contains gluten)), Water, Salt",
            {
                "expected_names": ["Flour", "Water", "Salt"],
                "expect_sub": {"Flour": ["Wheat (contains gluten)"]},
                "expect_additives": [],
            },
        ),
    ]

    for text, exp in samples:
        out = parse_ingredients(text)
        names = [ing["name"] for ing in out["ingredients"]]

        # Normalize case for comparison when expected lowercase
        exp_names_lower = [n.lower() for n in exp["expected_names"]]
        names_lower = [n.lower() for n in names]
        for en in exp_names_lower:
            assert en in names_lower, f"Expected ingredient '{en}' in parsed names {names} from '{text}'"

        # Check sub-ingredients
        for k, v in exp.get("expect_sub", {}).items():
            # find matching ingredient by lowercased name
            matches = [ing for ing in out["ingredients"] if ing["name"].lower() == k.lower()]
            assert matches, f"Expected ingredient '{k}' present to check sub-ingredients"
            got_sub = [s.lower() for s in matches[0]["sub_ingredients"]]
            for sub in v:
                assert sub.lower() in got_sub, f"Expected sub-ingredient '{sub}' for '{k}', got {got_sub}"

        # Check additives
        got_add = [a.upper() for a in out["additives"]]
        for a in exp.get("expect_additives", []):
            assert a.upper() in got_add, f"Expected additive '{a}' in {got_add}"

    print("All ingredient parser tests passed.")


if __name__ == "__main__":
    _run_tests()
