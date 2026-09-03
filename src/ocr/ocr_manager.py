"""Selection and fallback manager for local and Vision OCR providers."""
from typing import Optional

from .local_provider import LocalOCRProvider
from .ocr_provider import OCRProviderError, OCRResult
from .vision_provider import VisionAPIProvider, VisionAPIConfigurationError


class OCRManager:
    """Select local, API, or automatic fallback OCR mode."""

    def __init__(self, mode: str = "local", local_provider=None, api_provider=None, confidence_threshold: float = 0.70, min_tokens: int = 2):
        if mode not in {"local", "api", "auto"}:
            raise ValueError("OCR mode must be one of: local, api, auto")
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold must be between 0.0 and 1.0")
        if min_tokens < 0:
            raise ValueError("min_tokens must not be negative")
        self.mode = mode
        self.confidence_threshold = confidence_threshold
        self.min_tokens = min_tokens
        self.local_provider = local_provider
        self.api_provider = api_provider
        if mode in {"local", "auto"} and self.local_provider is None:
            self.local_provider = LocalOCRProvider()
        if mode in {"api", "auto"} and self.api_provider is None:
            self.api_provider = VisionAPIProvider()

    def _reliable(self, result: OCRResult) -> bool:
        if not result.text.strip():
            return False
        if result.confidence is not None and result.confidence < self.confidence_threshold:
            return False
        if len(result.text.split()) < self.min_tokens:
            return False
        return True

    def extract(self, image_path: str) -> OCRResult:
        if self.mode == "local":
            return self.local_provider.extract(image_path)
        if self.mode == "api":
            return self.api_provider.extract(image_path)

        try:
            local = self.local_provider.extract(image_path)
        except OCRProviderError:
            local = OCRResult("", None, source="local_easyocr", metadata={"error": "local OCR failed"})
        if self._reliable(local):
            local.metadata.update({"selected_provider": "local_easyocr", "fallback_occurred": False, "local_confidence": local.confidence, "final_confidence": local.confidence})
            return local
        try:
            api = self.api_provider.extract(image_path)
            api.metadata.update({"selected_provider": "vision_api", "fallback_occurred": True, "local_confidence": local.confidence, "final_confidence": api.confidence})
            return api
        except VisionAPIConfigurationError:
            local.metadata.update({"selected_provider": "local_easyocr", "fallback_occurred": False, "api_fallback_unavailable": True, "local_confidence": local.confidence, "final_confidence": local.confidence})
            return local


__all__ = ["OCRManager"]
