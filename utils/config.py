"""
utils/config.py
Centralised configuration — loads from .env and exposes typed settings.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── Locate the project root (two levels up from this file) ─────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root; silently skip if missing
load_dotenv(ROOT_DIR / ".env", override=False)


# ── Directories ────────────────────────────────────────────────────────────────
DATA_DIR       = ROOT_DIR / "data"
UPLOAD_DIR     = DATA_DIR / "uploads"
PROCESSED_DIR  = DATA_DIR / "processed"
INDEX_DIR      = DATA_DIR / "indexes"
REPORT_DIR     = DATA_DIR / "reports"
DB_PATH        = DATA_DIR / "scholarlens.db"

# Ensure all data directories exist at import time
for _d in (UPLOAD_DIR, PROCESSED_DIR, INDEX_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)


# ── API keys ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


# ── Embedding model ────────────────────────────────────────────────────────────
EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL",
    "all-MiniLM-L6-v2",          # ~80 MB, fast local model
)


# ── Gemini generation model ────────────────────────────────────────────────────
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# ── Chunking ───────────────────────────────────────────────────────────────────
CHUNK_SIZE: int    = int(os.getenv("CHUNK_SIZE", "600"))   # characters
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "80"))


# ── Retrieval ──────────────────────────────────────────────────────────────────
TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))


# ── Convenience helper ─────────────────────────────────────────────────────────
def gemini_configured() -> bool:
    """Return True when a Gemini API key is present."""
    return bool(GEMINI_API_KEY)
