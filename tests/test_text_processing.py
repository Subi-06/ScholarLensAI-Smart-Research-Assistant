"""
tests/test_text_processing.py
Unit tests for text cleaning and custom chunking in the RAG pipeline.
"""
from __future__ import annotations

import pytest
from services.text_processing import clean_text, chunk_text, chunk_pages


class TestCleanText:
    def test_clean_empty(self):
        assert clean_text("") == ""
        assert clean_text("   \n\t  ") == ""

    def test_ligatures_replaced(self):
        raw = "The efﬁcient clariﬁcation of ﬂow."
        cleaned = clean_text(raw)
        assert "efficient" in cleaned
        assert "clarification" in cleaned
        assert "flow" in cleaned
        assert "ﬁ" not in cleaned
        assert "ﬂ" not in cleaned

    def test_hyphenation_at_line_breaks(self):
        raw = "Deep neural networks use self-atten-\ntion mechanisms for trans-\nlation."
        cleaned = clean_text(raw)
        assert "self-attention" in cleaned
        assert "translation" in cleaned
        assert "atten-\ntion" not in cleaned

    def test_whitespace_normalization(self):
        raw = "Paragraph one with    extra   spaces.\n\n\n\nParagraph two."
        cleaned = clean_text(raw)
        assert "extra spaces." in cleaned
        assert "\n\n" in cleaned
        assert "\n\n\n\n" not in cleaned


class TestChunkText:
    def test_chunk_empty_text(self):
        chunks = chunk_text("", page_number=1)
        assert chunks == []

    def test_chunk_short_text(self):
        text = "This is a short single-sentence text."
        chunks = chunk_text(text, page_number=3, chunk_size=200, overlap=30)
        assert len(chunks) == 1
        assert chunks[0]["page_number"] == 3
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["text"] == text
        assert chunks[0]["char_start"] == 0
        assert chunks[0]["char_end"] == len(text)

    def test_chunk_long_text_overlap(self):
        # Generate 1500 characters of text
        text = (
            "Sentence one discusses deep learning architectures and attention. "
            "Sentence two elaborates on transformer models in natural language processing. "
            "Sentence three introduces multi-head self-attention mechanisms. "
            "Sentence four evaluates the empirical benchmarks on standard datasets. "
            "Sentence five discusses limitations and future research directions. "
        ) * 5

        chunk_size = 300
        overlap = 50
        chunks = chunk_text(text, page_number=2, chunk_size=chunk_size, overlap=overlap, start_chunk_index=10)

        assert len(chunks) > 1
        # Check start index offset
        assert chunks[0]["chunk_index"] == 10
        assert chunks[1]["chunk_index"] == 11

        for c in chunks:
            assert c["page_number"] == 2
            assert len(c["text"]) > 0
            assert c["char_start"] < c["char_end"]


class TestChunkPages:
    def test_chunk_multiple_pages(self):
        pages = [
            {"page": 1, "text": "Page one contains an introduction to scientific methods."},
            {"page": 2, "text": "Page two outlines the experimental setup and training procedures."},
            {"page": 3, "text": "Page three concludes with detailed empirical results and ablation studies."},
        ]

        chunks = chunk_pages(pages, chunk_size=100, overlap=20)
        assert len(chunks) >= 3

        # Indices must be strictly monotonically increasing from 0
        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(chunks)))

        # Pages must map accurately
        assert chunks[0]["page_number"] == 1
        assert any(c["page_number"] == 2 for c in chunks)
        assert any(c["page_number"] == 3 for c in chunks)
