"""Deterministic tests for local-first OCR routing and orchestration metadata."""
import os

from src.ocr import OCRManager, OCRResult, VisionAPIConfigurationError
from src.service import AnalysisService


class FakeProvider:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def extract(self, image_path):
        self.calls += 1
        if self.error:
            raise self.error
        return OCRResult(self.result.text, self.result.confidence, source=self.result.source)


def _run_tests():
    image_path = "fake-label.png"
    good_local = FakeProvider(OCRResult("Ingredients sugar milk", 0.95, source="local_easyocr"))
    api = FakeProvider(OCRResult("Ingredients api sugar", 0.99, source="vision_api"))
    result = OCRManager(mode="auto", local_provider=good_local, api_provider=api).extract(image_path)
    assert result.source == "local_easyocr"
    assert result.metadata["fallback_occurred"] is False
    assert api.calls == 0
    assert result.metadata["final_ocr_provider"] == "local_easyocr"
    assert "ocr_duration_ms" in result.metadata

    poor_local = FakeProvider(OCRResult("x", 0.2, source="local_easyocr"))
    fallback = OCRManager(mode="auto", local_provider=poor_local, api_provider=api).extract(image_path)
    assert fallback.source == "vision_api"
    assert fallback.metadata["fallback_occurred"] is True
    assert fallback.metadata["fallback_reason"] == "text_too_short"
    assert fallback.metadata["local_confidence"] == 0.2
    assert api.calls == 1

    empty_local = FakeProvider(OCRResult("", None, source="local_easyocr"))
    empty_api = FakeProvider(OCRResult("Ingredients api sugar", 0.9, source="vision_api"))
    empty_result = OCRManager(mode="auto", local_provider=empty_local, api_provider=empty_api).extract(image_path)
    assert empty_result.metadata["fallback_reason"] == "empty_text"
    assert empty_api.calls == 1

    unavailable = OCRManager(
        mode="auto",
        local_provider=poor_local,
        api_provider=FakeProvider(error=VisionAPIConfigurationError("missing config")),
    ).extract(image_path)
    assert unavailable.source == "local_easyocr"
    assert unavailable.metadata["api_fallback_unavailable"] is True
    assert unavailable.metadata["fallback_occurred"] is False

    local_manager = OCRManager(mode="local", local_provider=good_local, api_provider=api)
    local_manager.extract(image_path)
    assert api.calls == 1
    api_manager = OCRManager(mode="api", api_provider=api, local_provider=good_local)
    api_manager.extract(image_path)
    assert good_local.calls == 2

    old_values = {name: os.environ.get(name) for name in ("OCR_MIN_CONFIDENCE", "OCR_MIN_USEFUL_TOKENS", "OCR_MIN_TEXT_LENGTH")}
    try:
        os.environ["OCR_MIN_CONFIDENCE"] = "0.99"
        os.environ["OCR_MIN_USEFUL_TOKENS"] = "3"
        os.environ["OCR_MIN_TEXT_LENGTH"] = "2"
        configured_api = FakeProvider(OCRResult("API result", 0.9, source="vision_api"))
        configured = OCRManager(
            mode="auto",
            local_provider=FakeProvider(OCRResult("one two", 0.95, source="local_easyocr")),
            api_provider=configured_api,
        ).extract(image_path)
        assert configured.metadata["fallback_reason"] == "low_confidence"
        assert configured_api.calls == 1
    finally:
        for name, value in old_values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def manager_factory(**kwargs):
        return OCRManager(
            mode=kwargs["mode"],
            local_provider=FakeProvider(OCRResult("Ingredients: sugar, milk", 0.95, source="local_easyocr")),
            api_provider=FakeProvider(OCRResult("api", 0.9, source="vision_api")),
            confidence_threshold=kwargs["confidence_threshold"],
            min_tokens=kwargs["min_tokens"],
        )

    service_result = AnalysisService(ocr_manager_factory=manager_factory).analyze_image(image_path, ocr_mode="auto")
    assert service_result.ocr_result["metadata"]["final_ocr_provider"] == "local_easyocr"
    assert service_result.pipeline_result["ocr"]["text"] == service_result.ocr_text
    assert service_result.decision["overall_status"]
    assert service_result.trace["nodes"]
    print("All OCR routing and integration tests passed.")


if __name__ == "__main__":
    _run_tests()