"""
utils/helpers.py
Shared utility functions used across the application.
"""
from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ── File helpers ───────────────────────────────────────────────────────────────

def ensure_dir(path: str | Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Return the Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def file_hash(path: str | Path, algorithm: str = "sha256") -> str:
    """Return a hex digest of the file contents — used to detect duplicates."""
    h = hashlib.new(algorithm)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_filename(name: str) -> str:
    """Strip characters unsafe for filenames, replace spaces with underscores."""
    name = re.sub(r"[^\w\s\-.]", "", name)
    return re.sub(r"\s+", "_", name).strip("_")


# ── String helpers ─────────────────────────────────────────────────────────────

def truncate(text: str, max_chars: int = 300, ellipsis: str = "…") -> str:
    """Truncate *text* to *max_chars*, appending *ellipsis* if needed."""
    if not text:
        return ""
    return text[:max_chars] + ellipsis if len(text) > max_chars else text


def clean_whitespace(text: str) -> str:
    """Collapse multiple whitespace / newlines into single spaces."""
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    """Return approximate word count."""
    return len(text.split()) if text else 0


def clean_paper_title(title: str | None, file_path: str | Path | None = None) -> str:
    """
    Sanitize extracted paper title. If title contains unprintable unicode characters
    or is empty/corrupt, fall back to the cleaned filename.
    """
    raw = (title or "").strip()
    # Strip unprintable and private use characters
    cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f\uf000-\uf8ff]", "", raw).strip()
    if len(cleaned) >= 4 and any(c.isalnum() for c in cleaned):
        return cleaned

    if file_path:
        stem = Path(file_path).stem
        # Clean underscores and common suffixes
        clean_stem = re.sub(r"_+", " ", stem).strip()
        if clean_stem:
            return clean_stem

    return "Research Document"


# ── Date/time helpers ──────────────────────────────────────────────────────────

def utc_now() -> datetime:
    """Return the current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def timestamp_str() -> str:
    """Return a compact UTC timestamp string suitable for filenames."""
    return utc_now().strftime("%Y%m%d_%H%M%S")


def format_dt(dt: datetime | str | None) -> str:
    """
    Format a datetime or ISO string for display.
    Returns 'N/A' when the value is None or unparseable.
    """
    if dt is None:
        return "N/A"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    return dt.strftime("%d %b %Y, %H:%M")


# ── Number helpers ─────────────────────────────────────────────────────────────

def human_size(num_bytes: int) -> str:
    """Convert byte count to a human-readable string (e.g. 1.2 MB)."""
    for unit in ("B", "KB", "MB", "GB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024  # type: ignore[assignment]
    return f"{num_bytes:.1f} TB"


# ── Misc ───────────────────────────────────────────────────────────────────────

def flatten(nested: list[list[Any]]) -> list[Any]:
    """Flatten one level of nesting."""
    return [item for sublist in nested for item in sublist]
