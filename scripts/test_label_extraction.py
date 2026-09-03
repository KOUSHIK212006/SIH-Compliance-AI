"""Behavior tests for deterministic food-label field extraction."""
from src.label import LabelExtractionError, LabelFieldExtractor, extract_label_fields


def _run_tests():
    text = """Product Name: Cocoa Delight
Net Wt: 200 g
Serving Size: 25 g
Ingredients: Wheat Flour, Milk Powder, Cocoa Butter (12%), sugar
Allergen Information: Contains wheat and milk
Veg.
FSSAI License No: 12345678901234
Batch No: B-42
Mfg Date: 01/09/2026
Expiry Date: 2027-09-01
Best Before: 12 months
Country of Origin: India
Nutrition Facts: Calories 200
Manufactured by: Example Foods
"""
    result = extract_label_fields(text).to_dict()
    fields = result["fields"]
    assert fields["ingredients"]["value"] == "Wheat Flour, Milk Powder, Cocoa Butter (12%), sugar"
    assert fields["net_quantity"]["value"] == "200 g"
    assert fields["serving_size"]["value"] == "25 g"
    assert fields["allergen_information"]["value"] == "Contains wheat and milk"
    assert fields["fssai_license"]["value"] == "12345678901234"
    assert fields["batch_number"]["value"] == "B-42"
    assert fields["manufacturing_date"]["value"] == "01/09/2026"
    assert fields["expiry_date"]["value"] == "2027-09-01"
    assert fields["best_before"]["value"] == "12 months"
    assert fields["country_of_origin"]["value"] == "India"
    assert "Nutrition Facts" not in fields["ingredients"]["value"]
    assert fields["ingredients"]["source_text"]
    assert fields["ingredients"]["method"] == "header:ingredients_until_next_section"
    assert 0.0 <= fields["ingredients"]["confidence"] <= 1.0

    uppercase = extract_label_fields("INGREDIENTS: sugar\nNET WEIGHT: 1 kg\nMADE IN: India")
    assert uppercase.fields["ingredients"].value == "sugar"
    assert uppercase.fields["net_quantity"].value == "1 kg"
    assert uppercase.fields["country_of_origin"].value == "India"

    spaced = extract_label_fields("I n g r e d i e n t s : sugar, Milk Powder\nNet wt. 500 ml")
    assert spaced.fields["ingredients"].value == "sugar, Milk Powder"
    assert spaced.fields["net_quantity"].value == "500 ml"

    missing = extract_label_fields("Product Name: Sample\nNutrition Facts: Energy 100")
    assert all(value is None for name, value in missing.fields.items() if name != "ingredients")
    assert missing.fields["ingredients"] is None
    assert missing.warnings == ["Ingredients field not found"]

    empty = extract_label_fields("Ingredients:\nNutrition Facts: Energy 100")
    assert empty.fields["ingredients"] is None
    assert "Ingredients field not found" in empty.warnings

    false_positive = extract_label_fields("Our ingredients are carefully selected.\nProduct name: Example")
    assert false_positive.fields["ingredients"] is None

    repeated = extract_label_fields("Ingredients: wheat flour, cocoa butter\nStorage: Keep dry")
    assert repeated.fields["ingredients"].value == "wheat flour, cocoa butter"

    extractor = LabelFieldExtractor()
    assert extractor.extract("Ingredients: sugar").fields["ingredients"].value == "sugar"
    try:
        extract_label_fields(None)
        raise AssertionError("invalid input should fail")
    except LabelExtractionError:
        pass

    first = extract_label_fields(text).to_dict()
    second = extract_label_fields(text).to_dict()
    assert first == second
    print("All label extraction tests passed.")


if __name__ == "__main__":
    _run_tests()
