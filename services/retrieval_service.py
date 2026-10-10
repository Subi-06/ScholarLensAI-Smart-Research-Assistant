"""
services/retrieval_service.py
FAISS vector index management and semantic search.
Custom implementation without LangChain.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np
import faiss

from database import db
from services.embedding_service import embed_texts, embed_query
from utils import config


def build_index(embeddings: np.ndarray, index_path: str | Path) -> faiss.Index:
    """
    Build a flat inner-product (cosine similarity for normalized vectors)
    FAISS index and persist it to disk.
    """
    p = Path(index_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    dim = embeddings.shape[1] if embeddings.ndim == 2 and embeddings.shape[0] > 0 else 384
    index = faiss.IndexFlatIP(dim)

    if embeddings.shape[0] > 0:
        index.add(np.ascontiguousarray(embeddings, dtype=np.float32))

    faiss.write_index(index, str(p))
    return index


def load_index(index_path: str | Path) -> faiss.Index:
    """
    Load a FAISS index from disk.
    """
    p = Path(index_path)
    if not p.is_file():
        raise FileNotFoundError(f"FAISS index file not found at: {index_path}")
    return faiss.read_index(str(p))


def index_paper(paper_id: int) -> Path | None:
    """
    Generate embeddings for all chunks of a paper, construct a FAISS index,
    and save it in config.INDEX_DIR. Updates the database record with index_path.
    """
    chunks = db.get_chunks(paper_id)
    if not chunks:
        return None

    texts = [c["text"] for c in chunks]
    embeddings = embed_texts(texts)

    index_filename = f"paper_{paper_id}.index"
    target_path = Path(config.INDEX_DIR) / index_filename

    build_index(embeddings, target_path)

    # Update index_path in DB
    db.update_paper_metadata(paper_id, index_path=str(target_path))
    return target_path


def search_index(
    query_embedding: np.ndarray,
    index: faiss.Index,
    chunks: list[dict[str, Any]],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Search the FAISS index for the top_k most similar chunks.

    Returns:
        List of chunk dicts enriched with a 'score' key (cosine similarity in [-1, 1]).
    """
    if not chunks or index.ntotal == 0:
        return []

    query_vec = np.ascontiguousarray(query_embedding, dtype=np.float32).reshape(1, -1)
    k = min(top_k, len(chunks), index.ntotal)

    scores, indices = index.search(query_vec, k)

    results: list[dict[str, Any]] = []
    for score, idx in zip(scores[0], indices[0]):
        if 0 <= idx < len(chunks):
            chunk_copy = dict(chunks[idx])
            chunk_copy["score"] = float(score)
            results.append(chunk_copy)

    return results


def search_papers(
    query: str,
    paper_ids: list[int],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """
    Multi-paper semantic retrieval:
    1. Embeds the query
    2. Searches each paper's FAISS index
    3. Enriches results with paper title, authors, and page number
    4. Merges, ranks, and returns the global top_k chunks.
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query or not paper_ids:
        return []

    query_embedding = embed_query(cleaned_query)
    all_scored_chunks: list[dict[str, Any]] = []

    for pid in paper_ids:
        paper = db.get_paper(pid)
        if not paper:
            continue

        index_path = paper.get("index_path")
        # Build index on the fly if it hasn't been built yet
        if not index_path or not Path(index_path).is_file():
            new_path = index_paper(pid)
            if not new_path:
                continue
            index_path = str(new_path)

        try:
            index = load_index(index_path)
            chunks = db.get_chunks(pid)
            paper_matches = search_index(query_embedding, index, chunks, top_k=top_k)

            q_lower = cleaned_query.lower()
            is_author_q = any(w in q_lower for w in ("author", "who wrote", "writer", "affiliat", "researcher", "who is the", "who are the", "creator"))
            is_summary_q = any(w in q_lower for w in ("summar", "contribut", "abstract", "overview", "intro", "core concept", "about", "what is this paper", "methodology", "problem statement"))

            # If author query, guarantee Page 1 (chunk 0 with title and authors) is included
            if is_author_q and chunks:
                p1_chunks = [c for c in chunks if c.get("page_number", 1) == 1]
                if p1_chunks:
                    p1_match = dict(p1_chunks[0])
                    p1_match["paper_id"] = pid
                    p1_match["title"] = paper["title"]
                    p1_match["authors"] = paper.get("authors") or []
                    p1_match["year"] = paper.get("year")
                    p1_match["score"] = 1.0  # Top score guarantee
                    all_scored_chunks.append(p1_match)

            for match in paper_matches:
                match["paper_id"] = pid
                match["title"] = paper["title"]
                match["authors"] = paper.get("authors") or []
                match["year"] = paper.get("year")

                p_num = match.get("page_number", 1)
                text_lower = match.get("text", "").lower()

                # Penalize bibliography/reference sections for author queries
                if is_author_q:
                    if any(ref_mark in text_lower for ref_mark in ("references", "bibliography", "[1]", "[2]", "[10]", "vol.", "pp.")):
                        match["score"] = match.get("score", 0.0) - 0.4
                    elif p_num == 1:
                        match["score"] = match.get("score", 0.0) + 0.35

                # Context-aware boost: summary and overview queries prioritize abstract/intro pages (1-3)
                if is_summary_q and p_num <= 3:
                    match["score"] = match.get("score", 0.0) + 0.25

                all_scored_chunks.append(match)

        except Exception:
            # Continue gracefully if an index is corrupted or unreadable
            continue

    # Global sort descending by cosine similarity score & deduplicate by chunk id / index
    seen_chunks = set()
    unique_scored_chunks = []
    for c in sorted(all_scored_chunks, key=lambda x: x.get("score", -1.0), reverse=True):
        key = (c.get("paper_id"), c.get("page_number"), c.get("chunk_index"))
        if key not in seen_chunks:
            seen_chunks.add(key)
            unique_scored_chunks.append(c)

    return unique_scored_chunks[:top_k]
