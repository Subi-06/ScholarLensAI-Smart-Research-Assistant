"""
conftest.py
Global fixtures and sys.path setup for ScholarLens AI tests.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import utils.config as cfg
from database import db


@pytest.fixture(autouse=True)
def isolated_test_env(tmp_path):
    """
    Ensure each test runs against a clean, isolated SQLite DB and temporary data folders.
    """
    orig_db = cfg.DB_PATH
    orig_upload = cfg.UPLOAD_DIR
    orig_processed = cfg.PROCESSED_DIR
    orig_index = cfg.INDEX_DIR
    orig_report = cfg.REPORT_DIR
    orig_key = cfg.GEMINI_API_KEY

    cfg.DB_PATH = tmp_path / "test_scholarlens.db"
    cfg.UPLOAD_DIR = tmp_path / "uploads"
    cfg.PROCESSED_DIR = tmp_path / "processed"
    cfg.INDEX_DIR = tmp_path / "indexes"
    cfg.REPORT_DIR = tmp_path / "reports"
    cfg.GEMINI_API_KEY = ""

    for d in (cfg.UPLOAD_DIR, cfg.PROCESSED_DIR, cfg.INDEX_DIR, cfg.REPORT_DIR):
        d.mkdir(parents=True, exist_ok=True)

    db.init_db()

    yield tmp_path

    cfg.DB_PATH = orig_db
    cfg.UPLOAD_DIR = orig_upload
    cfg.PROCESSED_DIR = orig_processed
    cfg.INDEX_DIR = orig_index
    cfg.REPORT_DIR = orig_report
    cfg.GEMINI_API_KEY = orig_key
