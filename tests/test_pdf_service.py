"""
tests/test_pdf_service.py
Unit and integration tests for PDF ingestion and metadata extraction using PyMuPDF.
"""
from __future__ import annotations

from pathlib import Path
import pytest
import pymupdf

from database import db
from services.pdf_service import (
    save_uploaded_pdf,
    extract_text_from_pdf,
    get_pdf_metadata,
    ingest_pdf,
)


def create_sample_pdf(tmp_path: Path, filename: str = "sample_paper.pdf") -> Path:
    """Helper to create a realistic test PDF file using PyMuPDF."""
    pdf_path = tmp_path / filename
    doc = pymupdf.open()

    # Page 1
    page1 = doc.new_page()
    page1.insert_text(
        (50, 72),
        "Attention Across Multimodal Representations\n"
        "Alice Smith, Bob Jones\n\n"
        "Abstract: This research investigates self-attention across multimodal vision-language architectures.\n"
        "We demonstrate significant parameter efficiency compared to baseline models.\n\n"
        "1. Introduction\n"
        "Deep multimodal learning has seen rapid growth in recent years 2024.",
    )

    # Page 2
    page2 = doc.new_page()
    page2.insert_text(
        (50, 72),
        "2. Methodology and Experiments\n"
        "We evaluated our approach across three benchmark datasets.\n"
        "Empirical findings confirm robust generalisation with 15% fewer parameters.",
    )

    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


class TestPDFService:
    def test_save_uploaded_pdf(self, tmp_path):
        raw_bytes = b"%PDF-1.4 test dummy content"
        saved = save_uploaded_pdf(raw_bytes, "my paper (2024).pdf", upload_dir=tmp_path / "uploads")
        assert saved.exists()
        assert saved.is_file()
        assert "my_paper_2024.pdf" in saved.name
        assert saved.read_bytes() == raw_bytes

    def test_extract_text_from_pdf(self, tmp_path):
        pdf_path = create_sample_pdf(tmp_path)
        pages = extract_text_from_pdf(pdf_path)

        assert len(pages) == 2
        assert pages[0]["page"] == 1
        assert "Attention Across Multimodal" in pages[0]["text"]
        assert pages[1]["page"] == 2
        assert "Methodology and Experiments" in pages[1]["text"]

    def test_extract_missing_pdf_raises_error(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_text_from_pdf(tmp_path / "nonexistent.pdf")

    def test_get_pdf_metadata(self, tmp_path):
        pdf_path = create_sample_pdf(tmp_path)
        pages = extract_text_from_pdf(pdf_path)
        meta = get_pdf_metadata(pdf_path, first_page_text=pages[0]["text"])

        assert meta["page_count"] == 2
        assert "Attention Across Multimodal" in meta["title"]
        assert "self-attention across multimodal" in meta["abstract"].lower()
        assert meta["year"] == 2024

    def test_ingest_pdf_pipeline(self, tmp_path):
        pdf_path = create_sample_pdf(tmp_path)
        pdf_bytes = pdf_path.read_bytes()

        # Ingestion run 1: should succeed
        res1 = ingest_pdf(pdf_bytes, "sample_paper.pdf")
        assert res1["status"] == "success"
        assert res1["paper_id"] is not None
        assert res1["page_count"] == 2
        assert res1["chunk_count"] > 0

        # Verify DB has paper and chunks
        paper = db.get_paper(res1["paper_id"])
        assert paper is not None
        assert paper["status"] == "ready"
        assert paper["page_count"] == 2

        chunks = db.get_chunks(res1["paper_id"])
        assert len(chunks) == res1["chunk_count"]
        assert chunks[0]["page_number"] in [1, 2]

        # Ingestion run 2 with same bytes: should detect duplicate
        res2 = ingest_pdf(pdf_bytes, "sample_paper_copy.pdf")
        assert res2["status"] == "duplicate"
        assert res2["paper_id"] == res1["paper_id"]
