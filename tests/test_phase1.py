"""
tests/test_phase1.py
Phase 1 tests — database initialisation and basic CRUD.
"""
from __future__ import annotations

import pytest
from database import db


class TestInitDB:
    def test_init_creates_tables(self):
        db.init_db()
        with db.get_conn() as conn:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        assert "papers" in tables
        assert "chunks" in tables
        assert "chat_sessions" in tables
        assert "chat_messages" in tables
        assert "gap_analyses" in tables

    def test_init_idempotent(self):
        """Running init_db twice must not raise."""
        db.init_db()
        db.init_db()


class TestStats:
    def test_get_stats_returns_zero_on_empty_db(self):
        stats = db.get_stats()
        assert stats["total_papers"] == 0
        assert stats["processed_papers"] == 0
        assert stats["chat_sessions"] == 0
        assert stats["questions_asked"] == 0
        assert stats["gap_analyses"] == 0

    def test_get_stats_keys_present(self):
        stats = db.get_stats()
        required = {
            "total_papers",
            "processed_papers",
            "chat_sessions",
            "questions_asked",
            "gap_analyses",
        }
        assert required.issubset(stats.keys())


class TestPapersCRUD:
    def test_insert_and_get_paper(self):
        pid = db.insert_paper(
            file_path="/tmp/test.pdf",
            file_hash="abc123",
            title="Test Paper",
            authors=["Alice", "Bob"],
            year=2024,
            abstract="A test abstract.",
            page_count=10,
            word_count=5000,
        )
        assert isinstance(pid, int) and pid > 0
        paper = db.get_paper(pid)
        assert paper is not None
        assert paper["title"] == "Test Paper"
        assert paper["authors"] == ["Alice", "Bob"]
        assert paper["year"] == 2024
        assert paper["status"] == "uploaded"

    def test_paper_exists_by_hash(self):
        db.insert_paper(
            file_path="/tmp/unique.pdf",
            file_hash="unique_hash_xyz",
            title="Unique Paper",
        )
        assert db.paper_exists("unique_hash_xyz") is True
        assert db.paper_exists("nonexistent_hash") is False

    def test_update_paper_status(self):
        pid = db.insert_paper(
            file_path="/tmp/status_test.pdf",
            file_hash="hash_status_test",
            title="Status Test",
        )
        db.update_paper_status(pid, "ready")
        paper = db.get_paper(pid)
        assert paper["status"] == "ready"

    def test_update_paper_status_with_error(self):
        pid = db.insert_paper(
            file_path="/tmp/error_test.pdf",
            file_hash="hash_error_test",
            title="Error Test",
        )
        db.update_paper_status(pid, "error", error_msg="Extraction failed.")
        paper = db.get_paper(pid)
        assert paper["status"] == "error"
        assert paper["error_msg"] == "Extraction failed."

    def test_get_all_papers(self):
        pid = db.insert_paper(
            file_path="/tmp/p1.pdf",
            file_hash="hash_p1",
            title="P1",
        )
        papers = db.get_all_papers()
        assert len(papers) == 1
        assert papers[0]["id"] == pid

    def test_get_papers_by_status(self):
        db.insert_paper(
            file_path="/tmp/p_ready.pdf",
            file_hash="hash_p_ready",
            title="Ready Paper",
        )
        # Update to ready
        papers = db.get_all_papers()
        db.update_paper_status(papers[0]["id"], "ready")

        ready = db.get_papers_by_status("ready")
        assert len(ready) == 1
        assert ready[0]["status"] == "ready"

    def test_delete_paper(self):
        pid = db.insert_paper(
            file_path="/tmp/del_test.pdf",
            file_hash="hash_del_test",
            title="Delete Me",
        )
        db.delete_paper(pid, remove_file=False)
        assert db.get_paper(pid) is None


class TestConfig:
    def test_config_loads(self):
        from utils.config import ROOT_DIR, CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RESULTS

        assert ROOT_DIR.exists()
        assert isinstance(CHUNK_SIZE, int) and CHUNK_SIZE > 0
        assert isinstance(CHUNK_OVERLAP, int) and CHUNK_OVERLAP >= 0
        assert isinstance(TOP_K_RESULTS, int) and TOP_K_RESULTS > 0

    def test_gemini_configured_false_without_key(self, monkeypatch):
        import utils.config as cfg

        monkeypatch.setattr(cfg, "GEMINI_API_KEY", "")
        assert cfg.gemini_configured() is False

    def test_gemini_configured_true_with_key(self, monkeypatch):
        import utils.config as cfg

        monkeypatch.setattr(cfg, "GEMINI_API_KEY", "fake-key-123")
        assert cfg.gemini_configured() is True


class TestHelpers:
    def test_truncate_long_string(self):
        from utils.helpers import truncate

        result = truncate("a" * 400, max_chars=300)
        assert len(result) == 301

    def test_truncate_short_string(self):
        from utils.helpers import truncate

        short = "hello"
        assert truncate(short, max_chars=300) == "hello"

    def test_human_size(self):
        from utils.helpers import human_size

        assert "KB" in human_size(2048)
        assert "MB" in human_size(2 * 1024 * 1024)

    def test_safe_filename(self):
        from utils.helpers import safe_filename

        result = safe_filename("Hello World! (2024).pdf")
        assert " " not in result
        assert "!" not in result

    def test_word_count(self):
        from utils.helpers import word_count

        assert word_count("one two three") == 3
        assert word_count("") == 0
