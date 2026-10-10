"""
services/pdf_service.py
PDF ingestion, text extraction, and metadata parsing using PyMuPDF (pymupdf).
Custom implementation without LangChain.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import pymupdf

from database import db
from services.text_processing import clean_text, chunk_pages
from utils import config
from utils.helpers import safe_filename


def save_uploaded_pdf(file_bytes: bytes, filename: str, upload_dir: str | Path | None = None) -> Path:
    """
    Write uploaded bytes to disk under upload_dir with a sanitized filename.
    Returns the Path to the saved file.
    """
    if upload_dir is None:
        upload_dir = config.UPLOAD_DIR
    dest_dir = Path(upload_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    sanitized = safe_filename(filename)
    if not sanitized.lower().endswith(".pdf"):
        sanitized += ".pdf"

    target_path = dest_dir / sanitized

    # If a file with the same name exists, prepend a brief hash slice to avoid collision
    if target_path.exists():
        short_hash = hashlib.sha256(file_bytes).hexdigest()[:8]
        stem = target_path.stem
        target_path = dest_dir / f"{stem}_{short_hash}.pdf"

    target_path.write_bytes(file_bytes)
    return target_path


def extract_text_from_pdf(file_path: str | Path) -> list[dict[str, Any]]:
    """
    Extract text from a PDF file page by page using PyMuPDF.

    Returns:
        List of dicts: [
            {"page": int, "text": str, "char_count": int},
            ...
        ] (1-indexed page numbers)
    Raises:
        FileNotFoundError: if file_path does not exist.
        RuntimeError: if PyMuPDF cannot open or parse the document.
    """
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"PDF file not found at: {file_path}")

    try:
        doc = pymupdf.open(str(p))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF '{p.name}': {exc}") from exc

    pages: list[dict[str, Any]] = []
    try:
        for idx in range(len(doc)):
            page = doc[idx]
            text = page.get_text("text") or ""
            pages.append(
                {
                    "page": idx + 1,
                    "text": text,
                    "char_count": len(text),
                }
            )
    finally:
        doc.close()

    return pages


def get_pdf_metadata(file_path: str | Path, first_page_text: str = "") -> dict[str, Any]:
    """
    Extract title, authors, year, abstract, and page count from a PDF.
    Combines embedded PDF metadata with intelligent layout/text heuristics.
    """
    p = Path(file_path)
    if not p.is_file():
        raise FileNotFoundError(f"PDF file not found: {file_path}")

    try:
        doc = pymupdf.open(str(p))
    except Exception as exc:
        raise RuntimeError(f"Failed to open PDF '{p.name}': {exc}") from exc

    page_count = len(doc)
    doc_meta = doc.metadata or {}

    if not first_page_text and page_count > 0:
        first_page_text = doc[0].get_text("text") or ""

    # Second page text for multi-page abstract checks
    second_page_text = ""
    if page_count > 1:
        second_page_text = doc[1].get_text("text") or ""

    doc.close()

    # 1. Title Extraction
    title = (doc_meta.get("title") or "").strip()
    generic_titles = {"untitled", "document", "microsoft word", "paper", "manuscript"}
    if not title or any(g in title.lower() for g in generic_titles) or title.endswith(".pdf"):
        # Heuristic: Find first prominent non-empty line on the first page
        lines = [line.strip() for line in first_page_text.splitlines() if line.strip()]
        if lines:
            # Often first line or line before "Abstract" / authors is the title
            candidate_title = lines[0]
            if len(candidate_title) < 200:
                title = candidate_title

        # Ultimate fallback: Cleaned file stem
        if not title or any(g in title.lower() for g in generic_titles):
            title = p.stem.replace("_", " ").replace("-", " ").strip()

    # 2. Author Extraction
    authors_raw = (doc_meta.get("author") or "").strip()
    authors: list[str] = []
    if authors_raw:
        # Split by comma or semicolon or 'and'
        split_authors = re.split(r"[,;]|\band\b", authors_raw)
        authors = [a.strip() for a in split_authors if a.strip() and len(a.strip()) > 1]

    # 3. Year Extraction
    year: int | None = None
    creation_date = (doc_meta.get("creationDate") or "").strip()
    if creation_date:
        # Format often D:YYYYMMDD...
        match = re.search(r"\b(19\d{2}|20\d{2})\b", creation_date)
        if match:
            year = int(match.group(1))

    if year is None and first_page_text:
        # Look for 4-digit year in copyright or dates on first page
        year_match = re.search(r"\b(19[89]\d|20[0-2]\d)\b", first_page_text[:1500])
        if year_match:
            year = int(year_match.group(1))

    # 4. Abstract Extraction
    combined_front = f"{first_page_text}\n{second_page_text}"
    abstract = ""
    abstract_match = re.search(
        r"(?is)\babstract\b[\s:\-–—\.]+(.*?)(?=\b(?:1[\.\s]|I[\.\s]|introduction|keywords|index terms|categories)\b|\Z)",
        combined_front,
    )
    if abstract_match:
        extracted = abstract_match.group(1).strip()
        # Clean extracted abstract
        cleaned_abs = clean_text(extracted)
        if len(cleaned_abs) > 30:  # Must be substantial to be an abstract
            abstract = cleaned_abs[:1500]  # Cap at reasonable length

    return {
        "title": title,
        "authors": authors,
        "year": year,
        "abstract": abstract,
        "page_count": page_count,
    }


def ingest_pdf(file_bytes: bytes, filename: str) -> dict[str, Any]:
    """
    Ingest a PDF from raw bytes:
    1. Check for duplicates via SHA-256
    2. Save file to uploads folder
    3. Extract page-level text via PyMuPDF
    4. Extract metadata (title, authors, year, abstract)
    5. Clean and chunk text with page tracking
    6. Store paper and chunks in SQLite database
    7. Update status to 'ready'

    Returns dict with status ('success' | 'duplicate' | 'error') and details.
    """
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # 1. Deduplication check
    if db.paper_exists(file_hash):
        existing_papers = db.get_all_papers()
        match = next((p for p in existing_papers if p.get("file_hash") == file_hash), None)
        title = match["title"] if match else filename
        return {
            "status": "duplicate",
            "message": f"Paper '{title}' (or identical PDF content) is already uploaded.",
            "file_hash": file_hash,
            "paper_id": match["id"] if match else None,
        }

    # 2. Save file
    try:
        saved_path = save_uploaded_pdf(file_bytes, filename)
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to save file: {exc}",
        }

    paper_id: int | None = None
    try:
        # 3. Extract text
        pages = extract_text_from_pdf(saved_path)
        total_words = sum(len(p.get("text", "").split()) for p in pages)
        first_page_txt = pages[0]["text"] if pages else ""

        # 4. Metadata
        meta = get_pdf_metadata(saved_path, first_page_text=first_page_txt)

        # 5. Insert paper row
        paper_id = db.insert_paper(
            file_path=str(saved_path),
            file_hash=file_hash,
            title=meta.get("title") or filename,
            authors=meta.get("authors") or [],
            year=meta.get("year"),
            abstract=meta.get("abstract") or "",
            page_count=len(pages),
            word_count=total_words,
        )

        db.update_paper_status(paper_id, "processing")

        # 6. Chunking
        chunks = chunk_pages(pages, chunk_size=config.CHUNK_SIZE, overlap=config.CHUNK_OVERLAP)

        # 7. Insert chunks
        if chunks:
            db.insert_chunks(paper_id, chunks)
            # 8. Generate FAISS vector index
            from services.retrieval_service import index_paper
            index_paper(paper_id)

        # 9. Mark ready
        db.update_paper_status(paper_id, "ready")

        return {
            "status": "success",
            "paper_id": paper_id,
            "title": meta.get("title") or filename,
            "authors": meta.get("authors") or [],
            "year": meta.get("year"),
            "page_count": len(pages),
            "word_count": total_words,
            "chunk_count": len(chunks),
            "message": f"Successfully processed '{meta.get('title') or filename}' ({len(pages)} pages, {len(chunks)} chunks).",
        }

    except Exception as exc:
        if paper_id is not None:
            db.update_paper_status(paper_id, "error", error_msg=str(exc))
        return {
            "status": "error",
            "message": f"Failed to process '{filename}': {exc}",
            "paper_id": paper_id,
        }
