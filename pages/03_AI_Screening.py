"""
pages/03_AI_Screening.py
Evidence-based AI Screening module for systematic literature filtering.
Configurable criteria, transparent reasoning, and human-in-the-loop review overrides.
"""
from __future__ import annotations

import streamlit as st
from database import db
from services.screening_service import screen_corpus
from utils.helpers import truncate

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">AI Screening</div>
            <div class="sl-header-subtitle">Systematic title and abstract screening against configurable inclusion and exclusion criteria</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.info(
    "Methodology Note: Automated screening serves as an assistive filter. "
    "Per systematic review protocols (such as PRISMA), manual verification of borderline and excluded studies is advised."
)
st.markdown("<hr style='margin: 1rem 0 1.25rem; border-color: #1E293B;'>", unsafe_allow_html=True)

ready_papers = db.get_papers_by_status("ready")
if not ready_papers:
    st.info("No processed documents available in the library. Please upload PDFs in the Paper Library first.")
    st.stop()

# ── Screening Criteria Configuration ───────────────────────────────────────────
with st.expander("Screening Criteria Configuration", expanded=True):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Inclusion Criteria**")
        inc_kw_str = st.text_input(
            "Topic keywords (comma-separated)",
            value=st.session_state.get("scr_inc_kw", "attention, transformer, deep learning"),
            help="Documents must contain at least one of these terms in their title or abstract.",
        )
        match_mode = st.radio(
            "Inclusion matching rule",
            options=["Match ANY keyword", "Match ALL keywords"],
            horizontal=True,
            index=0,
        )
        min_year = st.number_input(
            "Minimum publication year",
            min_value=1980,
            max_value=2030,
            value=int(st.session_state.get("scr_min_year", 2017)),
        )

    with col2:
        st.markdown("**Exclusion Criteria**")
        exc_kw_str = st.text_input(
            "Exclusion keywords (comma-separated)",
            value=st.session_state.get("scr_exc_kw", "survey, review, tutorial"),
            help="Documents containing any of these terms will be flagged for exclusion.",
        )
        max_year = st.number_input(
            "Maximum publication year",
            min_value=1980,
            max_value=2030,
            value=int(st.session_state.get("scr_max_year", 2026)),
        )
        req_abstract = st.checkbox(
            "Flag documents with missing abstract as 'NEEDS REVIEW'",
            value=True,
        )

    btn_run = st.button("Run Screening Evaluation", type="primary")

include_keywords = [k.strip() for k in inc_kw_str.split(",") if k.strip()]
exclude_keywords = [k.strip() for k in exc_kw_str.split(",") if k.strip()]
criteria = {
    "include_keywords": include_keywords,
    "exclude_keywords": exclude_keywords,
    "min_year": min_year,
    "max_year": max_year,
    "require_abstract": req_abstract,
    "match_all_includes": (match_mode == "Match ALL keywords"),
}

if "screening_results" not in st.session_state or btn_run:
    results = screen_corpus(ready_papers, criteria)
    st.session_state["screening_results"] = {r["paper_id"]: r for r in results}

screening_dict = st.session_state.get("screening_results", {})

if "screening_overrides" not in st.session_state:
    st.session_state["screening_overrides"] = {}

total_papers = len(ready_papers)
included_count = 0
excluded_count = 0
review_count = 0

for p in ready_papers:
    pid = p["id"]
    decision = st.session_state["screening_overrides"].get(
        pid,
        screening_dict.get(pid, {}).get("decision", "NEEDS REVIEW"),
    )
    if decision == "INCLUDE":
        included_count += 1
    elif decision == "EXCLUDE":
        excluded_count += 1
    else:
        review_count += 1

# ── Metric Cards ───────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Screened Documents", total_papers)
m2.metric("Included", included_count)
m3.metric("Excluded", excluded_count)
m4.metric("Needs Manual Review", review_count)

st.divider()

# ── Tabs & Display ────────────────────────────────────────────────────────────
tab_all, tab_inc, tab_exc, tab_rev = st.tabs(
    [
        f"All ({total_papers})",
        f"Included ({included_count})",
        f"Excluded ({excluded_count})",
        f"Needs Review ({review_count})",
    ]
)


def render_paper_card(paper: dict):
    pid = paper["id"]
    eval_res = screening_dict.get(pid, {})
    current_decision = st.session_state["screening_overrides"].get(
        pid, eval_res.get("decision", "NEEDS REVIEW")
    )
    is_overridden = pid in st.session_state["screening_overrides"]

    badge_map = {
        "INCLUDE": ("badge-ready", "INCLUDED"),
        "EXCLUDE": ("badge-error", "EXCLUDED"),
        "NEEDS REVIEW": ("badge-process", "NEEDS REVIEW"),
    }
    badge_class, badge_label = badge_map.get(current_decision, ("badge-uploaded", current_decision))
    override_note = " (Manual override applied)" if is_overridden else ""

    st.markdown(
        f"""
        <div class="sl-card">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:6px;">
                <div class="sl-card-title">{paper['title']} ({paper.get('year') or 'N/A'})</div>
                <span class="badge {badge_class}">{badge_label}</span>
            </div>
            <div class="sl-card-body">
                <strong>Evaluation Detail:</strong> {eval_res.get('reason', 'N/A')}{override_note}<br><br>
                <strong>Abstract:</strong> {truncate(paper.get('abstract') or 'Abstract not detected.', 260)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_ov1, col_ov2, col_ov3 = st.columns([1, 1, 4])
    if col_ov1.button("Set as Included", key=f"btn_inc_{pid}"):
        st.session_state["screening_overrides"][pid] = "INCLUDE"
        st.rerun()
    if col_ov2.button("Set as Excluded", key=f"btn_exc_{pid}"):
        st.session_state["screening_overrides"][pid] = "EXCLUDE"
        st.rerun()
    if is_overridden:
        if col_ov3.button("Reset to Automated Decision", key=f"btn_rst_{pid}"):
            st.session_state["screening_overrides"].pop(pid, None)
            st.rerun()


with tab_all:
    for p in ready_papers:
        render_paper_card(p)

with tab_inc:
    inc_papers = [
        p for p in ready_papers
        if st.session_state["screening_overrides"].get(p["id"], screening_dict.get(p["id"], {}).get("decision")) == "INCLUDE"
    ]
    if not inc_papers:
        st.info("No documents currently marked as Included.")
    for p in inc_papers:
        render_paper_card(p)

with tab_exc:
    exc_papers = [
        p for p in ready_papers
        if st.session_state["screening_overrides"].get(p["id"], screening_dict.get(p["id"], {}).get("decision")) == "EXCLUDE"
    ]
    if not exc_papers:
        st.info("No documents currently marked as Excluded.")
    for p in exc_papers:
        render_paper_card(p)

with tab_rev:
    rev_papers = [
        p for p in ready_papers
        if st.session_state["screening_overrides"].get(p["id"], screening_dict.get(p["id"], {}).get("decision")) == "NEEDS REVIEW"
    ]
    if not rev_papers:
        st.info("No documents currently flagged as Needs Review.")
    for p in rev_papers:
        render_paper_card(p)
