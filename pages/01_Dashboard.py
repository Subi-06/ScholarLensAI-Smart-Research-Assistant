"""
pages/01_Dashboard.py
ScholarLens AI — Executive Research Intelligence Dashboard.
Presents verified metrics, recent document activity, and quick access workflows.
"""
from __future__ import annotations

import streamlit as st
from database.db import get_stats, get_recent_papers
from utils.helpers import format_dt, truncate
from utils.config import gemini_configured

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Overview Dashboard</div>
            <div class="sl-header-subtitle">Agentic literature synthesis, evidence extraction, and systematic research gap discovery</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── API Status Banner ─────────────────────────────────────────────────────────
if not gemini_configured():
    st.info(
        "Notice: Operating in local extractive mode. "
        "Configure GEMINI_API_KEY in .env to enable generative LLM synthesis and comparative summaries."
    )

# ── Key Performance & Corpus Metrics ──────────────────────────────────────────
stats = get_stats()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Indexed Documents", stats["total_papers"])
c2.metric("Ready for Analysis", stats["processed_papers"])
c3.metric("Research Sessions", stats["chat_sessions"])
c4.metric("Queries Processed", stats["questions_asked"])
c5.metric("Gap Syntheses", stats["gap_analyses"])

st.markdown("<hr style='margin: 1.25rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

# ── Main Dashboard Layout ─────────────────────────────────────────────────────
left, right = st.columns([2, 1], gap="large")

# ── Recent Documents Section ──────────────────────────────────────────────────
with left:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Recent Document Ingestion
        </div>
        """,
        unsafe_allow_html=True,
    )
    recent = get_recent_papers(limit=5)
    if not recent:
        st.markdown(
            """
            <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #334155;">
                <div style="font-weight: 600; color: #F8FAFC; margin-bottom: 4px;">No Publications Indexed Yet</div>
                <div style="font-size: 0.85rem; color: #94A3B8; margin-bottom: 12px;">
                    Upload your research papers in PDF format or search academic archives to start exploring.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for paper in recent:
            status = paper.get("status", "uploaded")
            badge_class = {
                "ready": "badge-ready",
                "processing": "badge-process",
                "uploaded": "badge-uploaded",
                "error": "badge-error",
            }.get(status, "badge-uploaded")

            year_str = f" ({paper['year']})" if paper.get("year") else ""
            st.markdown(
                f"""
                <div class="sl-card">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:4px;">
                        <div class="sl-card-title">{truncate(paper['title'], 80)}{year_str}</div>
                        <span class="badge {badge_class}">{status}</span>
                    </div>
                    <div class="sl-card-body">
                        {truncate(paper.get('abstract') or 'Abstract text not detected in document metadata.', 170)}
                        <div style="color:#94A3B8; font-size:0.75rem; margin-top:8px;">
                            Ingested {format_dt(paper.get('created_at'))} &nbsp;·&nbsp; {paper.get('page_count', 0)} pages &nbsp;·&nbsp; {paper.get('word_count', 0):,} words
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

# ── Quick Action Workflows ────────────────────────────────────────────────────
with right:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Research Modules
        </div>
        """,
        unsafe_allow_html=True,
    )

    actions = [
        ("Research Chat", "Dual-pane workstation with grounded answers and literature search.", "Chat"),
        ("Paper Search", "Query Springer, IEEE, arXiv, and Semantic Scholar indexes.", "Search"),
        ("Paper Library", "Upload, parse, and inspect multi-page PDF documents.", "Library"),
        ("Methodology Comparison", "Structured cross-document matrix across 8 research dimensions.", "Comparison"),
        ("Research Gaps", "Author limitation harvesting and novel experiment formulation.", "Gaps"),
        ("Synthesis Reports", "Generate publication-grade literature review summaries.", "Reports"),
    ]

    for title, desc, tag in actions:
        st.markdown(
            f"""
            <div class="sl-card" style="padding: 0.95rem 1.15rem; margin-bottom: 0.65rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                    <span style="font-weight: 600; font-size: 0.88rem; color: #818CF8;">{title}</span>
                    <span class="badge badge-uploaded" style="font-size: 0.65rem;">{tag}</span>
                </div>
                <div style="font-size: 0.8rem; color: #94A3B8; line-height: 1.45;">{desc}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr style='margin: 1.5rem 0 1rem; border-color: #1E293B;'>", unsafe_allow_html=True)
st.caption(
    "ScholarLens AI — Agentic Literature Survey & Evidence-Based Research Gap Discovery Platform."
)
