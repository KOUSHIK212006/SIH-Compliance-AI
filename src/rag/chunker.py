"""Deterministic page-aware text chunking."""
import hashlib
import re
from typing import Any, Dict, List

from .models import EvidenceChunk


class ChunkingError(ValueError):
    pass


def chunk_document(document: Dict[str, Any], chunk_size: int = 1000, overlap: int = 150) -> List[EvidenceChunk]:
    """Chunk loaded document pages by words without crossing page boundaries."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ChunkingError("chunk_size must be positive and overlap must be smaller than chunk_size")
    metadata = document.get("metadata") or {}
    document_id = metadata.get("document_id")
    if not document_id:
        raise ChunkingError("document metadata requires document_id")

    chunks: List[EvidenceChunk] = []
    for page in document.get("pages", []):
        text = str(page.get("text", "")).strip()
        if not text:
            continue
        page_number = page.get("page")
        words = text.split()
        start = 0
        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end]).strip()
            if chunk_text:
                section = _section_for_text(chunk_text, metadata.get("section"))
                chunk_id = hashlib.sha1(f"{document_id}:{page_number}:{start}:{chunk_text}".encode("utf-8")).hexdigest()
                chunk_metadata = dict(metadata)
                chunk_metadata.update({"page": page_number, "section": section})
                chunks.append(EvidenceChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=chunk_text,
                    metadata=chunk_metadata,
                    page=page_number,
                    section=section,
                    source=metadata.get("source"),
                    authority=metadata.get("authority"),
                ))
            if end == len(words):
                break
            start = end - overlap
    return chunks


def _section_for_text(text: str, fallback: Any) -> Any:
    match = re.search(r"\b(?:section|appendix|chapter)\s+[A-Za-z0-9. -]+", text, re.IGNORECASE)
    return match.group(0).strip() if match else fallback


__all__ = ["ChunkingError", "chunk_document"]
