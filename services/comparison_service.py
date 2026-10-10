"""
services/comparison_service.py
Structured methodology and findings comparison across multiple research papers.
Custom implementation utilizing Pandas and grounded evidence extraction.
"""
from __future__ import annotations

import re
from typing import Any
import pandas as pd

from database import db
from services.retrieval_service import search_papers
from services.llm_service import extract_structured, _configure_genai
from utils import config

# Default standard comparison dimensions
ALL_DIMENSIONS = [
    "Research Objective",
    "Algorithm / Method",
    "Dataset",
    "Experimental Setup",
    "Evaluation Metrics",
    "Key Findings",
    "Limitations",
    "Future Work",
]


def _heuristic_extract_dimension(dimension: str, paper: dict[str, Any], chunks: list[dict[str, Any]]) -> str:
    """Heuristic fallback when LLM is unavailable: finds relevant sentences in chunks."""
    kw_map = {
        "Research Objective": ["objective", "propose", "aim", "investigate", "introduce", "goal"],
        "Algorithm / Method": ["algorithm", "architecture", "method", "model", "network", "framework"],
        "Dataset": ["dataset", "benchmark", "corpus", "data", "samples", "evaluat"],
        "Experimental Setup": ["setup", "experiment", "training", "parameter", "hyperparameter", "gpu"],
        "Evaluation Metrics": ["metric", "accuracy", "f1", "bleu", "loss", "precision", "recall", "auc"],
        "Key Findings": ["finding", "result", "demonstrate", "show", "outperform", "achieve", "superior"],
        "Limitations": ["limitation", "drawback", "failure", "weakness", "restricted", "threat"],
        "Future Work": ["future work", "future research", "extension", "in future", "remain to be"],
    }
    keywords = kw_map.get(dimension, [dimension.lower()])
    corpus = (paper.get("abstract") or "") + "\n" + "\n".join(c.get("text", "") for c in chunks[:5])

    sentences = re.split(r"(?<=[.!?])\s+", corpus)
    matches = []
    for s in sentences:
        s_clean = s.strip()
        if len(s_clean) > 25 and any(kw in s_clean.lower() for kw in keywords):
            matches.append(s_clean)
            if len(matches) >= 2:
                break

    if matches:
        return " ".join(matches)
    return f"Details on '{dimension}' not explicitly identified in available excerpts."


def extract_paper_dimension(paper_id: int, dimension: str) -> str:
    """Extract a specific research dimension for a given paper."""
    paper = db.get_paper(paper_id)
    if not paper:
        return "Paper not found."

    chunks = db.get_chunks(paper_id)
    if not chunks:
        return paper.get("abstract") or "No text available."

    # Search for top-relevant chunks for this dimension
    relevant_chunks = search_papers(
        query=f"{dimension} in research methodology",
        paper_ids=[paper_id],
        top_k=3,
    )
    context_text = "\n\n".join(c.get("text", "") for c in relevant_chunks)
    if paper.get("abstract"):
        context_text = f"Abstract: {paper['abstract']}\n\nExcerpts:\n{context_text}"

    if _configure_genai():
        instruction = (
            f"You are analysing an academic paper titled '{paper['title']}'.\n"
            f"Extract a concise, factual summary (1 to 3 sentences) for the dimension: '{dimension}'.\n"
            f"Base your answer strictly on the provided text. If not mentioned, state 'Not reported'."
        )
        data = extract_structured(
            text=context_text,
            instruction=f"{instruction}\nReturn JSON format: {{\"summary\": \"...\"}}",
        )
        if isinstance(data, dict) and data.get("summary"):
            return data["summary"]

    return _heuristic_extract_dimension(dimension, paper, relevant_chunks or chunks)


def compare_papers(
    paper_ids: list[int],
    dimensions: list[str] | None = None,
) -> pd.DataFrame:
    """
    Generate a comparison table comparing papers across structured dimensions.

    Returns:
        pd.DataFrame where index is Paper Title and columns are dimensions.
    """
    if not dimensions:
        dimensions = ALL_DIMENSIONS[:5]

    data: dict[str, list[str]] = {dim: [] for dim in dimensions}
    paper_labels: list[str] = []

    for pid in paper_ids:
        paper = db.get_paper(pid)
        if not paper:
            continue

        label = f"{paper['title']} ({paper.get('year') or 'N/A'})"
        paper_labels.append(label)

        for dim in dimensions:
            summary = extract_paper_dimension(pid, dim)
            data[dim].append(summary)

    df = pd.DataFrame(data, index=paper_labels)
    df.index.name = "Paper"
    return df
