"""Behavior tests for the FastAPI backend layer."""
import io

from fastapi.testclient import TestClient

import src.api.routes as routes
from src.api.app import app


def _pipeline_report():
    return {
        "product": {"product_name": "Test Product"},
        "ingredients": {"normalized": [{"raw": "Sugar", "canonical_name": "sugar", "ingredient_type": "ingredient", "additive_code": None}]},
        "analysis": {"ingredient_results": [{
            "raw": "Sugar", "canonical_name": "sugar", "status": "known", "category": "sweetener",
            "function": "sweetening", "potential_concerns": [], "confidence": 0.9, "requires_review": False,
        }]},
        "compliance": {"findings": []}, "evidence": [], "explanations": [], "errors": [],
        "summary": {"requires_review": False},
    }


def _run_tests():
    client = TestClient(app)
    assert client.get("/health").json() == {"status": "ok"}

    valid = client.post("/analyze-text", json={
        "product_name": "Example Product",
        "ingredient_text": "Ingredients: sugar, milk powder, cocoa butter",
    })
    assert valid.status_code == 200
    body = valid.json()
    assert {"product_name", "overall_status", "ingredient_assessments", "compliance_findings", "health_findings", "evidence", "explanations", "confidence", "uncertainty", "recommendations"}.issubset(body)
    assert body["product_name"] == "Example Product"
    assert body["ingredient_assessments"]

    repeat = client.post("/analyze-text", json={"ingredient_text": "Ingredients: sugar"})
    repeat_again = client.post("/analyze-text", json={"ingredient_text": "Ingredients: sugar"})
    assert repeat.status_code == repeat_again.status_code == 200
    assert repeat.json() == repeat_again.json()

    empty = client.post("/analyze-text", json={"ingredient_text": ""})
    assert empty.status_code == 422
    malformed = client.post("/analyze-text", content=b"{not-json", headers={"content-type": "application/json"})
    assert malformed.status_code == 422

    original_pipeline = routes.run_product_pipeline
    routes.run_product_pipeline = lambda **kwargs: _pipeline_report()
    try:
        image = client.post(
            "/analyze-image",
            files={"file": ("label.png", io.BytesIO(b"\x89PNG\r\n\x1a\nTEST"), "image/png")},
        )
    finally:
        routes.run_product_pipeline = original_pipeline
    assert image.status_code == 200
    assert image.json()["product_name"] == "Test Product"

    invalid_type = client.post(
        "/analyze-image",
        files={"file": ("label.txt", io.BytesIO(b"not an image"), "text/plain")},
    )
    assert invalid_type.status_code == 415

    invalid_content = client.post(
        "/analyze-image",
        files={"file": ("label.png", io.BytesIO(b"not png"), "image/png")},
    )
    assert invalid_content.status_code == 400

    original_pipeline = routes.run_product_pipeline
    routes.run_product_pipeline = lambda **kwargs: {"status": "ocr_failed"}
    try:
        ocr_error = client.post(
            "/analyze-image",
            files={"file": ("label.png", io.BytesIO(b"\x89PNG\r\n\x1a\nTEST"), "image/png")},
        )
    finally:
        routes.run_product_pipeline = original_pipeline
    assert ocr_error.status_code == 422
    assert "Traceback" not in ocr_error.text

    original_pipeline = routes.run_product_pipeline
    routes.run_product_pipeline = lambda **kwargs: (_ for _ in ()).throw(RuntimeError("internal detail"))
    try:
        internal = client.post("/analyze-text", json={"ingredient_text": "Ingredients: sugar"})
    finally:
        routes.run_product_pipeline = original_pipeline
    assert internal.status_code == 500
    assert internal.json()["detail"] == "Text analysis failed"
    assert "internal detail" not in internal.text

    print("All API tests passed.")


if __name__ == "__main__":
    _run_tests()
