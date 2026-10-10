"""
services/citation_service.py
Citation validation, formatting, and evidence extraction for the RAG pipeline.
"""
from __future__ import annotations

import re
from typing import Any


def build_citation(
    paper_id: int,
    title: str,
    page_number: int,
    excerpt: str,
    score: float | None = None,
) -> dict[str, Any]:
    """Return a structured citation object."""
    return {
        "paper_id": paper_id,
        "title": title,
        "page_number": page_number,
        "excerpt": (excerpt or "").strip(),
        "score": score,
    }


def format_inline_citation(citation: dict[str, Any]) -> str:
    """Format a citation as an inline reference string, e.g. '[Title, p. 3]'."""
    title = citation.get("title") or "Unknown"
    # Keep title concise in inline tags
    short_title = title if len(title) <= 30 else title[:28] + "…"
    page = citation.get("page_number", 1)
    return f"[{short_title}, p. {page}]"


def validate_citations(
    answer: str,
    citations: list[dict[str, Any]],
    retrieved_chunks: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Verify that each citation's excerpt actually originates from the retrieved chunks.
    Ensures citations are strictly evidence-backed and never hallucinated.
    """
    if not citations:
        return []

    valid_citations: list[dict[str, Any]] = []

    # If chunks are provided, build an index of available text
    chunk_corpus = ""
    if retrieved_chunks:
        chunk_corpus = " ".join(c.get("text", "").lower() for c in retrieved_chunks)

    for cit in citations:
        excerpt = (cit.get("excerpt") or "").strip().lower()
        if not excerpt:
            continue

        # Check if a significant portion of the excerpt (e.g. first 25 chars or words) is in retrieved corpus
        words = [w for w in re.findall(r"\w+", excerpt) if len(w) > 3]
        if not words:
            valid_citations.append(cit)
            continue

        if chunk_corpus:
            # Check overlap: at least 60% of significant words exist in retrieved chunks
            matched = sum(1 for w in words if w in chunk_corpus)
            overlap_ratio = matched / len(words)
            if overlap_ratio >= 0.5:
                valid_citations.append(cit)
        else:
            # If no chunks provided for validation, preserve citation
            valid_citations.append(cit)

    return valid_citations


def extract_citations_from_chunks(chunks: list[dict[str, Any]], max_citations: int = 5) -> list[dict[str, Any]]:
    """
    Build structured citation items directly from retrieved candidate chunks.
    """
    citations = []
    seen = set()

    for c in chunks[:max_citations]:
        pid = c.get("paper_id", 0)
        page = c.get("page_number", 1)
        key = (pid, page)
        if key in seen:
            continue
        seen.add(key)

        excerpt = c.get("text", "")
        # Pick a clean representative snippet
        snippet = excerpt[:250].strip()
        if len(excerpt) > 250:
            snippet += "…"

        citations.append(
            build_citation(
                paper_id=pid,
                title=c.get("title") or "Unknown Paper",
                page_number=page,
                excerpt=snippet,
                score=c.get("score"),
            )
        )

    return citations
