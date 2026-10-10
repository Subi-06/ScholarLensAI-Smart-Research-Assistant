"""
tests/test_comparison_and_gaps.py
Unit and integration tests for comparison, gap analysis, paper search, and report generation services.
"""
from __future__ import annotations

import pandas as pd
import pytest

from database import db
from services.comparison_service import compare_papers, extract_paper_dimension
from services.gap_analysis import analyse_gaps
from services.paper_search import discover_papers, search_arxiv, search_semantic_scholar
from services.report_service import (
    generate_literature_survey,
    generate_comparison_report,
    generate_gap_report,
    generate_evidence_table_report,
    save_report,
)


@pytest.fixture
def sample_papers(tmp_path):
    """Seed two papers with chunks in the isolated database."""
    p1 = db.insert_paper(
        file_path="/tmp/p1.pdf",
        file_hash="hash_comp_1",
        title="Vision Transformer",
        authors=["Dosovitskiy", "Beyer"],
        year=2021,
        abstract="An image is worth 16x16 words. We apply standard transformer architectures to images directly.",
    )
    db.insert_chunks(
        p1,
        [
            {"chunk_index": 0, "page_number": 1, "text": "Our model applies self-attention across image patch sequences."},
            {"chunk_index": 1, "page_number": 2, "text": "The primary limitation is requiring huge pre-training datasets like JFT-300M."},
        ],
    )

    p2 = db.insert_paper(
        file_path="/tmp/p2.pdf",
        file_hash="hash_comp_2",
        title="Swin Transformer",
        authors=["Liu", "Lin"],
        year=2021,
        abstract="Hierarchical Vision Transformer using Shifted Windows.",
    )
    db.insert_chunks(
        p2,
        [
            {"chunk_index": 0, "page_number": 1, "text": "Shifted windows limit self-attention computation to non-overlapping local windows."},
            {"chunk_index": 1, "page_number": 2, "text": "A notable drawback is higher memory footprint during high-resolution dense prediction."},
        ],
    )
    return [p1, p2]


class TestComparisonService:
    def test_compare_papers(self, sample_papers):
        p1, p2 = sample_papers
        dims = ["Research Objective", "Algorithm / Method"]
        df = compare_papers([p1, p2], dimensions=dims)

        assert isinstance(df, pd.DataFrame)
        assert len(df.index) == 2
        assert list(df.columns) == dims
        assert len(df.loc[df.index[0], "Algorithm / Method"]) > 0

    def test_extract_dimension_fallback(self, sample_papers):
        p1 = sample_papers[0]
        res = extract_paper_dimension(p1, "Algorithm / Method")
        assert isinstance(res, str)
        assert len(res) > 10


class TestGapAnalysis:
    def test_analyse_gaps_returns_keys(self, sample_papers):
        res = analyse_gaps(sample_papers, focus="Vision Models")
        assert "summary" in res
        assert "patterns" in res
        assert "gaps" in res
        assert "proposed_experiments" in res
        assert len(res["gaps"]) > 0

        # Check that DB saved the analysis
        db_analyses = db.get_gap_analyses()
        assert len(db_analyses) >= 1

    def test_analyse_gaps_empty(self):
        res = analyse_gaps([])
        assert res["gaps"] == []


class TestReportService:
    def test_generate_literature_survey(self, sample_papers):
        md = generate_literature_survey(sample_papers, topic="State of Vision Transformers")
        assert "# State of Vision Transformers" in md
        assert "Vision Transformer" in md
        assert "Swin Transformer" in md
        assert "Surveyed Papers Index" in md

    def test_generate_comparison_report(self, sample_papers):
        md = generate_comparison_report(sample_papers, dimensions=["Algorithm / Method"])
        assert "Comparison Report" in md
        assert "Comparative Matrix" in md

    def test_generate_gap_report(self, sample_papers):
        analysis = analyse_gaps(sample_papers)
        md = generate_gap_report(analysis)
        assert "Research Gaps" in md
        assert "Actionable Experimental Blueprints" in md

    def test_generate_evidence_table_report(self, sample_papers):
        md = generate_evidence_table_report(sample_papers)
        assert "Research Evidence Table" in md
        assert "Vision Transformer" in md

    def test_save_report(self, tmp_path):
        saved = save_report("# Test Report", "sample_report.md", report_dir=tmp_path / "reports")
        assert saved.exists()
        assert saved.read_text(encoding="utf-8") == "# Test Report"


class TestPaperSearch:
    def test_discover_papers_empty(self):
        res = discover_papers("")
        assert res == []

    def test_search_academic_live(self):
        # Test real live query with limit 1
        res = search_arxiv("transformer attention", limit=1)
        assert isinstance(res, list)
        if res:
            paper = res[0]
            assert "title" in paper
            assert "url" in paper
            assert paper["source"] == "arXiv"

    def test_search_crossref_structure(self):
        from services.paper_search import search_crossref
        res = search_crossref("smartgrid", limit=2, publisher="IEEE")
        assert isinstance(res, list)
        if res:
            p = res[0]
            assert "title" in p
            assert "source" in p
            assert "url" in p
            assert "citation_count" in p
            assert "ieee" in p["source"].lower() or "institute of electrical" in p["source"].lower()

    def test_discover_papers_ieee_and_springer(self):
        res_ieee = discover_papers("smartgrid", source="IEEE", limit=2)
        assert isinstance(res_ieee, list)
        if res_ieee:
            assert any("ieee" in p["source"].lower() or "institute of electrical" in p["source"].lower() for p in res_ieee)

        res_springer = discover_papers("smartgrid", source="Springer", limit=2)
        assert isinstance(res_springer, list)
        if res_springer:
            assert any("springer" in p["source"].lower() or "nature" in p["source"].lower() for p in res_springer)
