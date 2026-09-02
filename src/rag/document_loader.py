"""Local PDF document loading. No network access or automatic downloads."""
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import DocumentMetadata


class DocumentLoaderError(Exception):
    """Raised when a local document cannot be loaded or contains no text."""


def load_pdf(path: str, metadata: Optional[DocumentMetadata] = None) -> Dict[str, Any]:
    """Extract text from a local PDF while preserving page boundaries."""
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise DocumentLoaderError(f"PDF file not found: {path}")
    if not pdf_path.is_file():
        raise DocumentLoaderError(f"PDF path is not a file: {path}")

    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentLoaderError("PDF loading requires pypdf; install it with: pip install pypdf") from exc

    try:
        reader = PdfReader(str(pdf_path))
        pages: List[Dict[str, Any]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append({"page": page_number, "text": text})
    except Exception as exc:
        raise DocumentLoaderError(f"Could not read PDF '{path}': {exc}") from exc

    if not any(page["text"] for page in pages):
        raise DocumentLoaderError(f"PDF contains no extractable text: {path}")

    checksum = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    if metadata is None:
        metadata = DocumentMetadata(
            document_id=pdf_path.stem,
            title=pdf_path.stem,
            source=str(pdf_path),
            source_type="local_document",
            checksum=checksum,
        )
    elif metadata.checksum is None:
        metadata.checksum = checksum

    return {"metadata": metadata.to_dict(), "pages": pages}


__all__ = ["DocumentLoaderError", "load_pdf"]
