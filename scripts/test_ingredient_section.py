"""Behavior tests for ingredient-section extraction and pipeline integration."""
from src.ingredients import extract_ingredient_section
from src.pipeline import run_product_pipeline


def _run_tests():
    cases = [
        ("Ingredients: sugar, milk powder, cocoa butter", "sugar, milk powder, cocoa butter"),
        ("INGREDIENTS: sugar, salt, water", "sugar, salt, water"),
        ("I n g r e d i e n t s : s u g a r , m i l k p o w d e r", "s u g a r , m i l k p o w d e r"),
        ("I N G R E D I E N T S\nsugar, salt", "sugar, salt"),
        ("Ingredients - wheat flour, sugar", "wheat flour, sugar"),
        ("Composition: cocoa butter, sugar", "cocoa butter, sugar"),
        ("Made with: wheat flour (12%), milk powder", "wheat flour (12%), milk powder"),
        ("iNgReDiEnTs : Sugar, MILK POWDER", "Sugar, MILK POWDER"),
    ]

    for text, expected in cases:
        result = extract_ingredient_section(text)
        assert result["found"] is True, text
        assert result["raw_text"] == expected, (text, result)
        assert 0.0 < result["confidence"] <= 1.0
        assert result["start_index"] < result["end_index"]

    stopped = extract_ingredient_section(
        "Product Name\nIngredients: wheat flour, sugar, cocoa butter\nNutrition Facts\nCalories 200"
    )
    assert stopped["raw_text"] == "wheat flour, sugar, cocoa butter"
    assert "Nutrition Facts" not in stopped["raw_text"]

    allergen = extract_ingredient_section(
        "Ingredients: milk powder (milk), cocoa butter\nAllergen Information: contains milk"
    )
    assert allergen["raw_text"] == "milk powder (milk), cocoa butter"

    noisy = extract_ingredient_section(
        "Product  Name\n I   n g r e d i e n t s  :  modified starch, cocoa butter\nStorage : keep cool"
    )
    assert noisy["raw_text"] == "modified starch, cocoa butter"

    no_section = extract_ingredient_section("Product Name\nNutrition Facts\nAddress: Example")
    assert no_section["found"] is False
    assert no_section["raw_text"] == ""
    assert no_section["confidence"] == 0.0
    assert "Ingredient section not found" in no_section["warnings"]

    empty = extract_ingredient_section("Ingredients:\nNutrition Facts\nCalories 100")
    assert empty["found"] is True
    assert empty["raw_text"] == ""
    assert "Ingredient section is empty" in empty["warnings"]

    prose = extract_ingredient_section(
        "Our ingredients are selected carefully.\nProduct Name\nNutrition Facts"
    )
    assert prose["found"] is False

    malformed = extract_ingredient_section(None)
    assert malformed["found"] is False
    assert malformed["warnings"] == ["OCR text must be a string"]

    report = run_product_pipeline(
        ocr_text="Product Name\nIngredients: sugar, milk powder, cocoa butter\nAllergens: contains milk"
    )
    assert report["ingredients"]["section_found"] is True
    assert report["ingredients"]["section_text"] == "sugar, milk powder, cocoa butter"
    assert report["ingredients"]["section_confidence"] > 0.0
    assert report["ingredients"]["raw"] == ["sugar", "milk powder", "cocoa butter"]

    report_no_section = run_product_pipeline(ocr_text="Nutrition Facts\nCalories 200")
    assert report_no_section["ingredients"]["section_found"] is False
    assert report_no_section["ingredients"]["section_text"] == ""

    print("All ingredient section tests passed.")


if __name__ == "__main__":
    _run_tests()
