"""
tests/test_citation_service.py
Unit tests for citation validation, inline citation formatting, and evidence extraction.
"""
from __future__ import annotations

import pytest
from services.citation_service import (
    build_citation,
    format_inline_citation,
    validate_citations,
    extract_citations_from_chunks,
)
from services.llm_service import generate_answer


class TestCitationService:
    def test_build_citation(self):
        cit = build_citation(
            paper_id=1,
            title="Attention Is All You Need",
            page_number=4,
            excerpt="Multi-head attention allows the model to jointly attend to information.",
            score=0.88,
        )
        assert cit["paper_id"] == 1
        assert cit["title"] == "Attention Is All You Need"
        assert cit["page_number"] == 4
        assert "Multi-head attention" in cit["excerpt"]
        assert cit["score"] == 0.88

    def test_format_inline_citation(self):
        cit = {
            "title": "BERT: Pre-training of Deep Bidirectional Transformers",
            "page_number": 2,
        }
        tag = format_inline_citation(cit)
        assert tag.startswith("[")
        assert tag.endswith("]")
        assert "p. 2" in tag

    def test_validate_citations_accepts_grounded_excerpt(self):
        retrieved_chunks = [
            {
                "paper_id": 1,
                "text": "Self-attention mechanisms calculate attention scores across tokens in parallel using queries, keys, and values.",
            }
        ]
        citation = {
            "paper_id": 1,
            "title": "Transformers",
            "page_number": 3,
            "excerpt": "attention scores across tokens in parallel using queries, keys, and values",
        }

        validated = validate_citations(
            answer="The model computes attention across tokens.",
            citations=[citation],
            retrieved_chunks=retrieved_chunks,
        )
        assert len(validated) == 1
        assert validated[0]["paper_id"] == 1

    def test_validate_citations_filters_unsupported_citation(self):
        retrieved_chunks = [
            {
                "paper_id": 1,
                "text": "This paper only discusses computer vision convolutional networks.",
            }
        ]
        hallucinated_citation = {
            "paper_id": 2,
            "title": "Quantum Computing",
            "page_number": 99,
            "excerpt": "superconducting qubits demonstrate exponential quantum supremacy over classical supercomputers",
        }

        validated = validate_citations(
            answer="Quantum supremacy is achieved.",
            citations=[hallucinated_citation],
            retrieved_chunks=retrieved_chunks,
        )
        assert len(validated) == 0

    def test_extract_citations_from_chunks(self):
        chunks = [
            {"paper_id": 10, "page_number": 1, "title": "Paper A", "text": "Snippet A with methodology details.", "score": 0.95},
            {"paper_id": 10, "page_number": 1, "title": "Paper A", "text": "Snippet A second chunk from same page.", "score": 0.90},
            {"paper_id": 11, "page_number": 4, "title": "Paper B", "text": "Snippet B with empirical evaluations.", "score": 0.85},
        ]
        cits = extract_citations_from_chunks(chunks)
        # Duplicate page for Paper A should be deduplicated
        assert len(cits) == 2
        assert cits[0]["paper_id"] == 10
        assert cits[1]["paper_id"] == 11

    def test_generate_answer_empty_retrieval(self):
        result = generate_answer("What is the loss function?", retrieved_chunks=[])
        assert "No relevant evidence was found" in result["answer"]
        assert result["citations"] == []

    def test_generate_answer_unconfigured_fallback(self, monkeypatch):
        import utils.config as cfg
        monkeypatch.setattr(cfg, "GEMINI_API_KEY", "")

        sample_chunk = [
            {"paper_id": 1, "title": "Paper Alpha", "page_number": 2, "text": "The learning rate was 1e-4 with AdamW optimizer.", "score": 0.92}
        ]
        result = generate_answer("What was the optimizer?", retrieved_chunks=sample_chunk)
        assert result["source"] == "grounded_synthesis"
        assert "AdamW" in result["answer"]
        assert len(result["citations"]) == 1
