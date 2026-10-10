"""
database/db.py
SQLite schema definition and CRUD helpers for ScholarLens AI.
All queries go through this module — no raw SQL in service or UI code.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

from utils import config


# ── Connection management ──────────────────────────────────────────────────────

@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    """Yield a connection with WAL mode, foreign keys, and Row factory."""
    conn = sqlite3.connect(str(config.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema ─────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT    NOT NULL DEFAULT 'Untitled',
    authors       TEXT,                      -- JSON array of strings
    year          INTEGER,
    abstract      TEXT,
    file_path     TEXT    NOT NULL,
    file_hash     TEXT    UNIQUE NOT NULL,   -- SHA-256 to prevent duplicates
    page_count    INTEGER DEFAULT 0,
    word_count    INTEGER DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'uploaded',
                                             -- uploaded | processing | ready | error
    error_msg     TEXT,
    index_path    TEXT,                      -- path to FAISS index file
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id      INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
    chunk_index   INTEGER NOT NULL,
    page_number   INTEGER NOT NULL,
    text          TEXT    NOT NULL,
    char_start    INTEGER,
    char_end      INTEGER
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL DEFAULT 'Unnamed session',
    paper_ids     TEXT,                      -- JSON array of paper IDs
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    INTEGER NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role          TEXT    NOT NULL,          -- user | assistant
    content       TEXT    NOT NULL,
    citations     TEXT,                      -- JSON array of citation objects
    created_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS gap_analyses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_ids     TEXT    NOT NULL,          -- JSON array
    summary       TEXT,
    gaps          TEXT,                      -- JSON array of gap objects
    created_at    TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_paper  ON chunks(paper_id);
CREATE INDEX IF NOT EXISTS idx_msgs_session  ON chat_messages(session_id);
"""


def init_db() -> None:
    """Create all tables and indexes if they do not already exist."""
    with get_conn() as conn:
        conn.executescript(_SCHEMA)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _from_json(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


# ── Papers CRUD ────────────────────────────────────────────────────────────────

def insert_paper(
    *,
    file_path: str,
    file_hash: str,
    title: str = "Untitled",
    authors: list[str] | None = None,
    year: int | None = None,
    abstract: str | None = None,
    page_count: int = 0,
    word_count: int = 0,
) -> int:
    """Insert a new paper row and return its ID."""
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO papers
                (title, authors, year, abstract, file_path, file_hash,
                 page_count, word_count, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'uploaded', ?, ?)
            """,
            (title, _to_json(authors), year, abstract,
             file_path, file_hash, page_count, word_count, now, now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_paper(paper_id: int) -> dict | None:
    """Return a single paper as a plain dict, or None if not found."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_paper(row)


def get_all_papers() -> list[dict]:
    """Return all papers ordered by creation date descending."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM papers ORDER BY created_at DESC"
        ).fetchall()
    return [_row_to_paper(r) for r in rows]


def get_papers_by_status(status: str) -> list[dict]:
    """Return papers filtered by status."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM papers WHERE status = ? ORDER BY created_at DESC",
            (status,),
        ).fetchall()
    return [_row_to_paper(r) for r in rows]


def paper_exists(file_hash: str) -> bool:
    """Return True if a paper with this hash is already stored."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM papers WHERE file_hash = ?", (file_hash,)
        ).fetchone()
    return row is not None


def update_paper_status(paper_id: int, status: str, error_msg: str | None = None) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET status=?, error_msg=?, updated_at=? WHERE id=?",
            (status, error_msg, _now(), paper_id),
        )


def update_paper_metadata(paper_id: int, **kwargs: Any) -> None:
    """Update arbitrary paper columns. Only known columns are allowed."""
    allowed = {
        "title", "authors", "year", "abstract", "page_count",
        "word_count", "status", "error_msg", "index_path",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    # JSON-encode list fields
    if "authors" in fields and isinstance(fields["authors"], list):
        fields["authors"] = _to_json(fields["authors"])
    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k}=?" for k in fields)
    values = list(fields.values()) + [paper_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE papers SET {set_clause} WHERE id=?", values)


def delete_paper(paper_id: int, remove_file: bool = True) -> None:
    if remove_file:
        paper = get_paper(paper_id)
        if paper:
            if paper.get("file_path"):
                try:
                    p = Path(paper["file_path"])
                    if p.is_file():
                        p.unlink()
                except OSError:
                    pass
            if paper.get("index_path"):
                try:
                    ip = Path(paper["index_path"])
                    if ip.is_file():
                        ip.unlink()
                except OSError:
                    pass
    with get_conn() as conn:
        conn.execute("DELETE FROM papers WHERE id=?", (paper_id,))


def _row_to_paper(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["authors"] = _from_json(d.get("authors"))
    return d


# ── Chunks CRUD ────────────────────────────────────────────────────────────────

def insert_chunks(paper_id: int, chunks: list[dict]) -> None:
    """
    Bulk-insert text chunks for a paper.
    Each dict must have: chunk_index, page_number, text, char_start, char_end.
    """
    rows = [
        (paper_id, c["chunk_index"], c["page_number"],
         c["text"], c.get("char_start"), c.get("char_end"))
        for c in chunks
    ]
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT INTO chunks (paper_id, chunk_index, page_number, text, char_start, char_end)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            rows,
        )


def get_chunks(paper_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chunks WHERE paper_id=? ORDER BY chunk_index",
            (paper_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_chunks(paper_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM chunks WHERE paper_id=?", (paper_id,))


# ── Chat CRUD ──────────────────────────────────────────────────────────────────

def create_chat_session(name: str, paper_ids: list[int]) -> int:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO chat_sessions (name, paper_ids, created_at) VALUES (?, ?, ?)",
            (name, _to_json(paper_ids), now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_chat_sessions() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_sessions ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["paper_ids"] = _from_json(d.get("paper_ids"))
        result.append(d)
    return result


def add_chat_message(
    session_id: int,
    role: str,
    content: str,
    citations: list[dict] | None = None,
) -> int:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_messages (session_id, role, content, citations, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, _to_json(citations), now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_chat_messages(session_id: int) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_messages WHERE session_id=? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["citations"] = _from_json(d.get("citations"))
        result.append(d)
    return result


# ── Gap Analyses CRUD ──────────────────────────────────────────────────────────

def save_gap_analysis(paper_ids: list[int], summary: str, gaps: Any) -> int:
    now = _now()
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO gap_analyses (paper_ids, summary, gaps, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (_to_json(paper_ids), summary, _to_json(gaps), now),
        )
        return cur.lastrowid  # type: ignore[return-value]


def get_gap_analyses() -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM gap_analyses ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["paper_ids"] = _from_json(d.get("paper_ids"))
        d["gaps"] = _from_json(d.get("gaps"))
        result.append(d)
    return result


# ── Statistics ─────────────────────────────────────────────────────────────────

def get_stats() -> dict[str, int]:
    """Return dashboard metric counts — all values are real DB counts."""
    with get_conn() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        ready    = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE status='ready'"
        ).fetchone()[0]
        sessions = conn.execute("SELECT COUNT(*) FROM chat_sessions").fetchone()[0]
        messages = conn.execute(
            "SELECT COUNT(*) FROM chat_messages WHERE role='user'"
        ).fetchone()[0]
        gaps     = conn.execute("SELECT COUNT(*) FROM gap_analyses").fetchone()[0]
    return {
        "total_papers":    total,
        "processed_papers": ready,
        "chat_sessions":   sessions,
        "questions_asked": messages,
        "gap_analyses":    gaps,
    }


def get_recent_papers(limit: int = 5) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM papers ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_paper(r) for r in rows]
