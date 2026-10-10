"""
tests/test_screening_service.py
Unit tests for the AI paper screening criteria engine.
"""
from __future__ import annotations

import pytest
from services.screening_service import screen_paper, screen_corpus


class TestScreeningService:
    def test_screen_paper_include_keyword(self):
        paper = {
            "id": 1,
            "title": "Self-Attention Architectures in Language Processing",
            "abstract": "We evaluate transformer architectures for semantic parsing.",
            "year": 2021,
        }
        criteria = {
            "include_keywords": ["transformer"],
            "exclude_keywords": [],
            "min_year": 2018,
        }
        res = screen_paper(paper, criteria)
        assert res["decision"] == "INCLUDE"
        assert "transformer" in res["matched_includes"]

    def test_screen_paper_exclude_keyword(self):
        paper = {
            "id": 2,
            "title": "A Comprehensive Survey on Deep Learning",
            "abstract": "We review deep learning progress over the past decade.",
            "year": 2022,
        }
        criteria = {
            "include_keywords": ["deep learning"],
            "exclude_keywords": ["survey", "review"],
        }
        res = screen_paper(paper, criteria)
        assert res["decision"] == "EXCLUDE"
        assert "survey" in res["matched_excludes"] or "review" in res["matched_excludes"]

    def test_screen_paper_min_year(self):
        paper = {
            "id": 3,
            "title": "Early Perceptron Experiments",
            "abstract": "Foundations of connectionist computing.",
            "year": 1995,
        }
        criteria = {
            "include_keywords": [],
            "exclude_keywords": [],
            "min_year": 2015,
        }
        res = screen_paper(paper, criteria)
        assert res["decision"] == "EXCLUDE"
        assert "1995" in res["reason"]

    def test_screen_paper_missing_abstract_needs_review(self):
        paper = {
            "id": 4,
            "title": "Conference Short Note",
            "abstract": "",
            "year": 2023,
        }
        criteria = {
            "include_keywords": ["deep learning"],
            "exclude_keywords": [],
            "require_abstract": True,
        }
        res = screen_paper(paper, criteria)
        assert res["decision"] == "NEEDS REVIEW"

    def test_screen_paper_match_all_includes(self):
        paper = {
            "id": 5,
            "title": "Multimodal Transformers for Speech",
            "abstract": "We study cross-attention between audio and transcript tokens.",
            "year": 2023,
        }
        criteria = {
            "include_keywords": ["multimodal", "robotics"],
            "exclude_keywords": [],
            "match_all_includes": True,
        }
        res = screen_paper(paper, criteria)
        assert res["decision"] == "NEEDS REVIEW"
        assert "robotics" in res["reason"]

    def test_screen_corpus(self):
        papers = [
            {"id": 1, "title": "Paper One", "abstract": "Deep learning research.", "year": 2020},
            {"id": 2, "title": "Paper Two Survey", "abstract": "Review article.", "year": 2020},
        ]
        criteria = {"include_keywords": ["learning"], "exclude_keywords": ["survey"]}
        results = screen_corpus(papers, criteria)
        assert len(results) == 2
        assert results[0]["decision"] == "INCLUDE"
        assert results[1]["decision"] == "EXCLUDE"
