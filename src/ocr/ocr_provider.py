"""Common OCR provider contract and normalized result model."""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol


@dataclass
class OCRResult:
    """Provider-neutral OCR output."""

    text: str
    confidence: Optional[float]
    bbox: Optional[Any] = None
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("OCR result text must be a string")
        if self.confidence is not None:
            self.confidence = max(0.0, min(1.0, float(self.confidence)))


class OCRProvider(Protocol):
    """Minimal interface implemented by OCR providers."""

    def extract(self, image_path: str) -> OCRResult:
        ...


class OCRProviderError(Exception):
    """Base exception for provider and manager failures."""


__all__ = ["OCRResult", "OCRProvider", "OCRProviderError"]
