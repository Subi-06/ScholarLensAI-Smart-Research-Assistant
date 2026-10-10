"""
services/text_processing.py
Text cleaning and chunking for the RAG pipeline.
Custom implementation without LangChain.
"""
from __future__ import annotations

import re
from typing import Any

# Common PDF ligatures mapping
_LIGATURES = {
    "ﬁ": "fi",
    "ﬂ": "fl",
    "ﬃ": "ffi",
    "ﬄ": "ffl",
    "ﬀ": "ff",
    "ﬅ": "ft",
    "ﬆ": "st",
}


def clean_text(text: str) -> str:
    """
    Remove noise from extracted PDF text:
    - Normalise unicode ligatures
    - Reconnect hyphenated words split across newlines
    - Standardise whitespace and paragraph breaks
    """
    if not text:
        return ""

    # Replace ligatures
    for lig, rep in _LIGATURES.items():
        text = text.replace(lig, rep)

    # Rejoin words hyphenated at line ends: "evalu-\nation" -> "evaluation"
    text = re.sub(r"(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)", r"\1\2", text)

    # Replace non-breaking spaces and strange unicode spaces with standard space
    text = re.sub(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]", " ", text)

    # Normalize double newlines (paragraphs) vs single newlines (within sentences)
    # Replace sequences of 3+ newlines with 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Replace multiple spaces with a single space
    text = re.sub(r"[ \t]+", " ", text)

    # Strip whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove repeated blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def chunk_text(
    text: str,
    page_number: int,
    chunk_size: int = 600,
    overlap: int = 80,
    start_chunk_index: int = 0,
) -> list[dict[str, Any]]:
    """
    Split text into overlapping chunks, tracking char boundaries and page numbers.
    Respects word boundaries near the split threshold where possible.

    Returns:
        List of {
            "chunk_index": int,
            "page_number": int,
            "text": str,
            "char_start": int,
            "char_end": int
        } dicts.
    """
    cleaned = clean_text(text)
    if not cleaned:
        return []

    # Ensure valid chunking parameters
    if chunk_size <= 0:
        chunk_size = 600
    if overlap >= chunk_size:
        overlap = max(0, chunk_size // 4)

    total_len = len(cleaned)
    if total_len <= chunk_size:
        return [
            {
                "chunk_index": start_chunk_index,
                "page_number": page_number,
                "text": cleaned,
                "char_start": 0,
                "char_end": total_len,
            }
        ]

    step = chunk_size - overlap
    chunks: list[dict[str, Any]] = []
    idx = start_chunk_index
    start = 0

    while start < total_len:
        end = min(start + chunk_size, total_len)

        # If not at the very end of text, attempt to break cleanly at a word/sentence boundary
        if end < total_len:
            # Look backwards from 'end' up to overlap distance for a space or punctuation
            search_window = cleaned[max(start, end - overlap):end]
            # Try to split at sentence end (. ! ? \n) or word space
            boundary_match = None
            for delim in [". ", "? ", "! ", "\n\n", "\n", " "]:
                pos = search_window.rfind(delim)
                if pos != -1:
                    boundary_match = max(start, end - overlap) + pos + len(delim)
                    break

            if boundary_match and boundary_match > start + (chunk_size // 3):
                end = boundary_match

        chunk_str = cleaned[start:end].strip()
        if chunk_str:
            chunks.append(
                {
                    "chunk_index": idx,
                    "page_number": page_number,
                    "text": chunk_str,
                    "char_start": start,
                    "char_end": end,
                }
            )
            idx += 1

        # Advance start
        if end >= total_len:
            break
        start = max(start + 1, end - overlap)

    return chunks


def chunk_pages(
    pages: list[dict[str, Any]],
    chunk_size: int = 600,
    overlap: int = 80,
) -> list[dict[str, Any]]:
    """
    Chunk a list of page dicts (from pdf_service) into a flat list of chunks.
    Each page dict must contain:
        - "page": int (1-indexed page number)
        - "text": str (page text)
    Assigns globally sequential chunk_index across pages.
    """
    all_chunks: list[dict[str, Any]] = []
    current_idx = 0

    for page_info in pages:
        page_num = page_info.get("page", 1)
        raw_text = page_info.get("text", "")

        page_chunks = chunk_text(
            text=raw_text,
            page_number=page_num,
            chunk_size=chunk_size,
            overlap=overlap,
            start_chunk_index=current_idx,
        )
        all_chunks.extend(page_chunks)
        current_idx += len(page_chunks)

    return all_chunks
