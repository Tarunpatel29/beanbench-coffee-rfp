"""Reads proposal PDFs and prepares text for evaluation and evidence search."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

MAX_DOCUMENT_CHARACTERS = 60_000


def extract_pdf(file_obj) -> dict:
    """Return clean text, a SHA-256 fingerprint, page count, and warnings."""
    name = getattr(file_obj, "name", "proposal.pdf")
    if not str(name).lower().endswith(".pdf"):
        raise ValueError("This file does not have a .pdf filename.")
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_obj, strict=True)
    except Exception as exc:
        raise ValueError(f"This file could not be opened as a PDF: {exc}") from exc
    if reader.is_encrypted:
        raise ValueError("This PDF is locked with a password. Please upload an unlocked PDF.")
    pages = [page.extract_text() or "" for page in reader.pages]
    text = re.sub(r"\s+", " ", " ".join(pages)).strip()
    if not text:
        raise ValueError("No readable text was found. This may be a scanned PDF; this demo does not include OCR.")
    raw = text.encode("utf-8")
    warnings = []
    if len(text) > MAX_DOCUMENT_CHARACTERS:
        text = text[:MAX_DOCUMENT_CHARACTERS]
        warnings.append(f"Proposal text was shortened to {MAX_DOCUMENT_CHARACTERS:,} characters.")
    return {"text": text, "page_count": len(pages), "sha256": hashlib.sha256(raw).hexdigest(),
            "warnings": warnings, "filename": Path(name).name}


def retrieve_evidence(text: str, query: str, limit: int = 3) -> list[str]:
    """Simple RAG-style retrieval: return the most relevant text passages."""
    passages = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if len(part.strip()) > 25]
    stop_words = {"the", "and", "for", "with", "from", "that", "this", "your", "their"}
    terms = set(re.findall(r"[a-z0-9]+", query.lower())) - stop_words
    scored = []
    for passage in passages:
        tokens = set(re.findall(r"[a-z0-9]+", passage.lower()))
        overlap = len(tokens & terms)
        if overlap:
            scored.append((overlap / max(1, len(terms)), passage))
    scored.sort(key=lambda item: (-item[0], len(item[1])))
    return [passage for _, passage in scored[:limit]]
