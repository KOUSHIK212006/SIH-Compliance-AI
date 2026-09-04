"""End-to-end validation for the canonical AnalysisService image path."""
import json
from pathlib import Path

from src.ocr import OCRManager, OCRResult
from src.service import AnalysisService, AnalysisServiceError
from src.trace import build_trace

from .run_demo import format_analysis_report, validate_image_path


class FakeProvider:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def extract(self, image_path):
        self.calls += 1
        return OCRResult(self.result.text, self.result.confidence, source=self.result.source)


def _run_tests():
    repository_root = Path(__file__).resolve().parents[1]
    sample_path = repository_root / "sample_package.png"
    assert validate_image_path(str(sample_path)) == sample_path

    sample_local = FakeProvider(OCRResult("Test Product\nNet wt 200g", 0.99, source="local_easyocr"))
    real_result = AnalysisService(
        ocr_manager_factory=lambda **kwargs: OCRManager(
            mode=kwargs["mode"], local_provider=sample_local,
            confidence_threshold=kwargs["confidence_threshold"], min_tokens=kwargs["min_tokens"]
        )
    ).analyze_image(str(sample_path), ocr_mode="local", product_data={"product_name": "Demo"})
    assert real_result.ocr_text
    assert real_result.ocr_result["confidence"] is not None
    assert real_result.ocr_result["source"] == "local_easyocr"
    assert isinstance(real_result.label_fields.get("fields"), dict)
    assert isinstance(real_result.pipeline_result, dict)
    assert isinstance(real_result.compliance_findings, list)
    assert isinstance(real_result.evidence, list)
    assert isinstance(real_result.decision, dict)
    assert real_result.decision.get("overall_status")
    assert real_result.trace.get("trace_id")
    assert format_analysis_report(real_result).startswith("=" * 50)

    local = FakeProvider(OCRResult("Ingredients: sugar, milk powder", 0.95, source="local_easyocr"))
    vision = FakeProvider(OCRResult("vision result", 0.9, source="vision_api"))

    def manager_factory(**kwargs):
        return OCRManager(mode=kwargs["mode"], local_provider=local, api_provider=vision,
                          confidence_threshold=kwargs["confidence_threshold"], min_tokens=kwargs["min_tokens"])

    result = AnalysisService(ocr_manager_factory=manager_factory).analyze_image(
        str(sample_path), ocr_mode="local", product_data={"product_name": "Integration Demo"}
    )
    assert result.ocr_text.startswith("Ingredients:")
    assert result.ingredients
    assert result.normalized_ingredients
    assert isinstance(result.label_fields["fields"], dict)
    assert isinstance(result.compliance_findings, list)
    assert isinstance(result.evidence, list)
    assert result.decision.get("overall_status")
    assert result.explanations
    assert len(result.trace["nodes"]) >= 3
    assert len({node["type"] for node in result.trace["nodes"]}) >= 3
    assert result.trace["edges"]
    assert not build_trace(result.pipeline_result, result.decision).validate()
    assert vision.calls == 0

    serialized = result.to_dict()
    json.dumps(serialized)
    serialized_json = result.to_json()
    assert "image_bytes" not in serialized_json
    assert "api_key" not in serialized_json.casefold()

    try:
        AnalysisService(ocr_manager_factory=lambda **kwargs: OCRManager(
            mode="local", local_provider=FakeProvider(OCRResult("", None, source="local_easyocr"))
        )).analyze_image(str(sample_path), ocr_mode="local")
        raise AssertionError("empty OCR should fail")
    except AnalysisServiceError as exc:
        assert "no text" in str(exc).casefold()

    try:
        validate_image_path(str(repository_root / "missing-image.png"))
        raise AssertionError("missing image should fail validation")
    except ValueError:
        pass

    print("All end-to-end tests passed.")


if __name__ == "__main__":
    _run_tests()