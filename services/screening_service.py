"""
services/screening_service.py
Automated paper screening engine with configurable inclusion and exclusion criteria.
Provides transparent reasoning and evaluation flags (PRISMA review aligned).
"""
from __future__ import annotations

import re
from typing import Any


def screen_paper(paper: dict[str, Any], criteria: dict[str, Any]) -> dict[str, Any]:
    """
    Evaluate a single paper against inclusion and exclusion criteria.

    Criteria options:
        - include_keywords (list[str]): Keywords that must appear
        - exclude_keywords (list[str]): Keywords that trigger exclusion
        - min_year (int | None): Minimum allowable publication year
        - max_year (int | None): Maximum allowable publication year
        - require_abstract (bool): If True, missing abstract triggers NEEDS REVIEW
        - match_all_includes (bool): If True, all inclusion keywords are required; else any

    Returns:
        Dict with decision ('INCLUDE', 'EXCLUDE', 'NEEDS REVIEW'), reason, and matched terms.
    """
    title = (paper.get("title") or "").strip()
    abstract = (paper.get("abstract") or "").strip()
    year = paper.get("year")

    corpus = f"{title} {abstract}".lower()

    include_keywords = [
        k.strip().lower() for k in criteria.get("include_keywords", []) if k.strip()
    ]
    exclude_keywords = [
        k.strip().lower() for k in criteria.get("exclude_keywords", []) if k.strip()
    ]
    min_year = criteria.get("min_year")
    max_year = criteria.get("max_year")
    require_abstract = criteria.get("require_abstract", False)
    match_all_includes = criteria.get("match_all_includes", False)

    # 1. Missing Abstract Check
    if not abstract:
        if require_abstract:
            return {
                "paper_id": paper.get("id"),
                "title": title,
                "year": year,
                "decision": "NEEDS REVIEW",
                "reason": "Missing abstract; full text must be reviewed manually.",
                "matched_includes": [],
                "matched_excludes": [],
            }

    # 2. Exclusion Keywords Check (Immediate Exclusion)
    matched_excludes = [
        k for k in exclude_keywords if re.search(r"\b" + re.escape(k) + r"\b", corpus)
    ]
    if matched_excludes:
        return {
            "paper_id": paper.get("id"),
            "title": title,
            "year": year,
            "decision": "EXCLUDE",
            "reason": f"Matched exclusion keyword(s): {', '.join(matched_excludes)}.",
            "matched_includes": [],
            "matched_excludes": matched_excludes,
        }

    # 3. Publication Year Checks
    if year is not None:
        if min_year is not None and year < min_year:
            return {
                "paper_id": paper.get("id"),
                "title": title,
                "year": year,
                "decision": "EXCLUDE",
                "reason": f"Published in {year}, which is earlier than minimum year {min_year}.",
                "matched_includes": [],
                "matched_excludes": [],
            }
        if max_year is not None and year > max_year:
            return {
                "paper_id": paper.get("id"),
                "title": title,
                "year": year,
                "decision": "EXCLUDE",
                "reason": f"Published in {year}, which exceeds maximum year {max_year}.",
                "matched_includes": [],
                "matched_excludes": [],
            }

    # 4. Inclusion Keywords Check
    matched_includes = [
        k for k in include_keywords if re.search(r"\b" + re.escape(k) + r"\b", corpus)
    ]

    if include_keywords:
        if match_all_includes:
            if len(matched_includes) == len(include_keywords):
                decision = "INCLUDE"
                reason = f"Satisfied all {len(include_keywords)} inclusion criteria."
            elif len(matched_includes) > 0:
                decision = "NEEDS REVIEW"
                missing = set(include_keywords) - set(matched_includes)
                reason = f"Partial match: matched {len(matched_includes)} criteria, missing: {', '.join(missing)}."
            else:
                decision = "EXCLUDE"
                reason = "None of the required inclusion keywords were found."
        else:
            if matched_includes:
                decision = "INCLUDE"
                reason = f"Matched inclusion keyword(s): {', '.join(matched_includes)}."
            else:
                decision = "EXCLUDE"
                reason = "None of the specified inclusion keywords were found."
    else:
        # No inclusion keywords specified
        decision = "INCLUDE"
        reason = "Satisfied temporal and exclusion criteria."

    return {
        "paper_id": paper.get("id"),
        "title": title,
        "year": year,
        "decision": decision,
        "reason": reason,
        "matched_includes": matched_includes,
        "matched_excludes": [],
    }


def screen_corpus(
    papers: list[dict[str, Any]],
    criteria: dict[str, Any],
) -> list[dict[str, Any]]:
    """Screen an entire list of papers against criteria."""
    return [screen_paper(p, criteria) for p in papers]
