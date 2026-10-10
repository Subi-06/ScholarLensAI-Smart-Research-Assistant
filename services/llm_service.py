"""
services/llm_service.py
Gemini API integration for RAG question answering, summarisation, and structured extraction.
Custom prompt construction without LangChain.
"""
from __future__ import annotations

import json
import re
from typing import Any

from services.citation_service import (
    extract_citations_from_chunks,
    format_inline_citation,
    validate_citations,
)
from utils import config

# Try importing google.generativeai
try:
    import google.generativeai as genai
    _HAS_GENAI = True
except ImportError:
    _HAS_GENAI = False


def _configure_genai() -> bool:
    """Configure the Gemini SDK if the API key is present."""
    if not _HAS_GENAI or not config.GEMINI_API_KEY:
        return False
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        return True
    except Exception:
        return False


def synthesize_grounded_answer(question: str, retrieved_chunks: list[dict[str, Any]]) -> str:
    """
    Synthesize a clean, direct, human-readable academic answer
    from retrieved evidence chunks without API latency or quota failures.
    """
    if not retrieved_chunks:
        return "No relevant excerpts were retrieved from the document to answer this question."

    q_lower = question.lower()
    is_author_q = any(w in q_lower for w in ("author", "who wrote", "writer", "affiliat", "researcher", "who is the", "who are the"))

    # Author query fallback
    if is_author_q:
        p1_chunks = [c for c in retrieved_chunks if c.get("page_number", 1) == 1]
        target_chunk = p1_chunks[0] if p1_chunks else retrieved_chunks[0]
        lines = [line.strip() for line in target_chunk.get("text", "").split("\n") if line.strip()]
        # Extract probable author names from early lines before abstract
        author_lines = []
        for line in lines[:8]:
            if any(term in line.lower() for term in ("abstract", "introduction", "smart grid", "framework", "index")):
                continue
            if len(line) < 45 and not line.startswith("http") and not line.startswith("["):
                author_lines.append(line)
        if author_lines:
            return "**Paper Authors & Affiliation:**\n\n" + "\n".join(f"- {a}" for a in author_lines[:6])

    # General query synthesis
    stop_words = {"what", "is", "the", "of", "this", "paper", "explain", "in", "and", "a", "an", "could", "you", "please", "about", "how", "why", "are", "do", "does"}
    q_words = set(re.findall(r"\w+", q_lower)) - stop_words

    salient_points: list[dict[str, Any]] = []
    for c in retrieved_chunks:
        page = c.get("page_number", 1)
        raw_text = c.get("text", "")
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_text) if len(s.strip()) > 35]
        for s in sentences:
            s_clean = re.sub(r"\s+", " ", s)
            score = sum(1 for w in q_words if w in s_clean.lower())
            salient_points.append({"page": page, "text": s_clean, "score": score})

    salient_points.sort(key=lambda x: x["score"], reverse=True)

    unique_points: list[dict[str, Any]] = []
    seen = set()
    for pt in salient_points:
        norm = pt["text"][:50].lower()
        if norm not in seen:
            seen.add(norm)
            unique_points.append(pt)
        if len(unique_points) >= 4:
            break

    if not unique_points:
        return retrieved_chunks[0].get("text", "")[:400]

    answer_parts = ["### Summary of Evidence\n"]
    for pt in unique_points:
        answer_parts.append(f"- **(Page {pt['page']})** {pt['text']}")

    return "\n\n".join(answer_parts)


def generate_answer(
    question: str,
    retrieved_chunks: list[dict[str, Any]],
    model_name: str | None = None,
) -> dict[str, Any]:
    """
    Generate an evidence-backed answer using Gemini or instant grounded synthesis.
    Eliminates quota failures and provides clear, human-readable answers.
    """
    if not retrieved_chunks:
        return {
            "answer": (
                "No relevant evidence was found in the selected papers for this question. "
                "Try refining your search terms or selecting additional papers."
            ),
            "citations": [],
            "source": "retrieval_empty",
        }

    citations = extract_citations_from_chunks(retrieved_chunks, max_citations=6)
    model_id = model_name or config.GEMINI_MODEL or "gemini-3.8-flash"

    # Fast synthesis fallback if Gemini is not configured or offline
    if not _configure_genai():
        return {
            "answer": synthesize_grounded_answer(question, retrieved_chunks),
            "citations": citations,
            "source": "grounded_synthesis",
        }

    # Format context for prompt
    context_blocks = []
    for idx, c in enumerate(retrieved_chunks):
        title = c.get("title", "Unknown")
        page = c.get("page_number", 1)
        text = c.get("text", "")
        context_blocks.append(
            f"[Source {idx + 1}] Paper: \"{title}\" | Page: {page}\nContent: {text}"
        )
    formatted_context = "\n\n".join(context_blocks)

    system_instruction = (
        "You are ScholarLens AI, an expert academic research assistant.\n"
        "Your goal is to provide clear, direct, precise, and easily understandable answers based STRICTLY on the provided research paper context.\n\n"
        "GUIDELINES:\n"
        "1. Give direct, precise answers to the user's question. Do NOT include robotic preambles or repetitive disclaimers.\n"
        "2. For author/researcher questions: State the paper's actual primary authors and their academic institution from Page 1. Do NOT list cited authors from the references list.\n"
        "3. For summary questions: Structure clearly with concise headings: Problem Statement, Core Methodology, and Key Contributions / Findings.\n"
        "4. For empirical or technical questions: Directly report the quantitative benchmarks, datasets, metrics, and comparisons.\n"
        "5. Include concise inline citations where appropriate (e.g., [Page X])."
    )

    prompt = (
        f"{system_instruction}\n\n"
        f"--- RETRIEVED RESEARCH EVIDENCE ---\n"
        f"{formatted_context}\n\n"
        f"--- USER QUESTION ---\n"
        f"{question}\n\n"
        f"--- CLEAR & PRECISE ANSWER ---"
    )

    try:
        model = genai.GenerativeModel(model_id)
        response = model.generate_content(prompt, request_options={"timeout": 15.0})
        answer_text = response.text if hasattr(response, "text") and response.text else ""
        if not answer_text or "exceeded your current quota" in answer_text.lower():
            raise RuntimeError("API quota unavailable")

        # Validate that citations reference valid evidence
        valid_cits = validate_citations(answer_text, citations, retrieved_chunks)

        return {
            "answer": answer_text,
            "citations": valid_cits if valid_cits else citations,
            "source": "gemini",
        }

    except Exception:
        # Instant fallback to high-quality synthesized response
        return {
            "answer": synthesize_grounded_answer(question, retrieved_chunks),
            "citations": citations,
            "source": "grounded_synthesis",
        }


def summarise_text(text: str, max_words: int = 200, model_name: str | None = None) -> str:
    """Summarise a block of academic text using Gemini or clean heuristic fallback."""
    if not text:
        return ""

    if not _configure_genai():
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."

    model_id = model_name or config.GEMINI_MODEL or "gemini-flash-latest"
    prompt = (
        f"Provide a concise academic summary in fewer than {max_words} words for the following text:\n\n{text[:4000]}"
    )

    try:
        model = genai.GenerativeModel(model_id)
        response = model.generate_content(prompt)
        return response.text.strip() if hasattr(response, "text") and response.text else text[:500]
    except Exception:
        return text[:500] + "..."


def extract_structured(text: str, instruction: str, model_name: str | None = None) -> dict[str, Any]:
    """
    Extract structured JSON data according to prompt instructions.
    """
    if not _configure_genai():
        return {}

    model_id = model_name or config.GEMINI_MODEL or "gemini-flash-latest"
    prompt = (
        f"{instruction}\n\n"
        f"Return ONLY valid JSON (no markdown fences, no explanatory text).\n\n"
        f"Text to analyse:\n{text[:6000]}"
    )

    try:
        model = genai.GenerativeModel(model_id)
        response = model.generate_content(prompt)
        raw_text = response.text.strip() if hasattr(response, "text") and response.text else "{}"

        # Clean JSON fences if model output them
        cleaned = re.sub(r"^```json\s*", "", raw_text)
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        return json.loads(cleaned)
    except Exception:
        return {}
