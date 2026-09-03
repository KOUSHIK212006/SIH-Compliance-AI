"""Local EasyOCR provider backed by the existing OCR engine."""
from typing import List, Optional

from .ocr_engine import OCRException, init_reader, ocr_image_path
from .ocr_provider import OCRProviderError, OCRResult


class LocalOCRProvider:
    """Use the existing EasyOCR implementation without duplicating it."""

    def __init__(self, languages: Optional[List[str]] = None, gpu: bool = False, reader=None):
        self.languages = languages or ["en"]
        self.gpu = gpu
        try:
            self.reader = reader or init_reader(self.languages, gpu=gpu)
        except Exception as exc:
            raise OCRProviderError(f"Local OCR initialization failed: {exc}") from exc

    def extract(self, image_path: str) -> OCRResult:
        try:
            result = ocr_image_path(image_path, langs=self.languages, gpu=self.gpu, reader=self.reader)
        except OCRException as exc:
            raise OCRProviderError(f"Local OCR failed: {exc}") from exc
        except Exception as exc:
            raise OCRProviderError("Local OCR failed") from exc
        return OCRResult(
            text=result.get("text", ""),
            confidence=result.get("mean_confidence"),
            bbox=result.get("details", []),
            source="local_easyocr",
            metadata={"details": result.get("details", []), "raw_results": result.get("raw_results", [])},
        )


__all__ = ["LocalOCRProvider"]
