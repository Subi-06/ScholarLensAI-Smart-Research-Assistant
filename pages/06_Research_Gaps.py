"""
pages/06_Research_Gaps.py
Evidence-based research gap discovery dashboard.
Presents author-reported limitations, cross-paper patterns, potential research gaps, and proposed experiments.
"""
from __future__ import annotations

import streamlit as st
from database import db
from services.gap_analysis import analyse_gaps
from utils.helpers import format_dt

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Research Gaps</div>
            <div class="sl-header-subtitle">Harvest author-reported limitations, identify recurring methodological omissions, and discover novel opportunities</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ready_papers = db.get_papers_by_status("ready")
if len(ready_papers) < 2:
    st.markdown(
        """
        <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #CBD5E1;">
            <div style="font-weight: 600; color: #0F172A; margin-bottom: 4px;">Minimum 2 Documents Required</div>
            <div style="font-size: 0.85rem; color: #64748B;">
                At least 2 processed publications are required for cross-paper gap synthesis. Please ingest additional publications in the Paper Library.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Selection & Scope ─────────────────────────────────────────────────────────
paper_map = {f"{p['title']} ({p.get('year') or 'N/A'})": p["id"] for p in ready_papers}

col_sel, col_focus = st.columns([1, 1])

with col_sel:
    selected_labels = st.multiselect(
        "Target documents for gap synthesis",
        options=list(paper_map.keys()),
        default=list(paper_map.keys()),
        help="Select the corpus of papers to analyze.",
    )

with col_focus:
    domain_focus = st.text_input(
        "Research scope / problem statement (optional)",
        placeholder="e.g. Parameter efficiency and out-of-distribution robustness",
        help="Provide a specific research domain to focus the gap analysis.",
    )

selected_ids = [paper_map[l] for l in selected_labels]

col_btn, _ = st.columns([1, 4])
btn_run = col_btn.button("Run Gap Analysis", type="primary", disabled=(len(selected_ids) < 2))

if len(selected_ids) < 2:
    st.warning("Please select at least 2 documents.")
    st.stop()

st.markdown("<hr style='margin: 1.25rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

analysis_key = f"gap_{'_'.join(str(i) for i in sorted(selected_ids))}_{domain_focus}"

if btn_run or ("active_gap_result" in st.session_state and st.session_state.get("gap_key") == analysis_key):
    if btn_run:
        with st.spinner("Harvesting limitations and synthesizing research gaps..."):
            res = analyse_gaps(selected_ids, focus=domain_focus)
            st.session_state["active_gap_result"] = res
            st.session_state["gap_key"] = analysis_key

    result = st.session_state.get("active_gap_result", {})

    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">
            Executive Synthesis
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(result.get("summary", "Analysis completed."))

    tab_gaps, tab_limits, tab_patterns, tab_exps = st.tabs(
        [
            f"Potential Gaps ({len(result.get('gaps', []))})",
            f"Author Limitations ({len(result.get('author_limitations', []))})",
            f"Recurring Patterns ({len(result.get('patterns', []))})",
            f"Proposed Experiments ({len(result.get('proposed_experiments', []))})",
        ]
    )

    with tab_gaps:
        for idx, gap in enumerate(result.get("gaps", [])):
            st.markdown(
                f"""
                <div class="sl-card">
                    <div class="sl-card-title" style="color:#818CF8; font-size:1rem;">
                        Gap #{idx + 1}: {gap.get('gap_title')}
                    </div>
                    <div class="sl-card-body">
                        <strong>Description:</strong> {gap.get('description')}<br><br>
                        <strong>Supporting Evidence:</strong> {gap.get('evidence')}<br><br>
                        <span style="display:inline-block; background:#1E1B4B; color:#A5B4FC; padding:4px 8px; border-radius:4px; font-weight:600; font-size:0.78rem; text-transform:uppercase;">
                            Expected Academic Impact: {gap.get('impact')}
                        </span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_limits:
        limits = result.get("author_limitations", [])
        if not limits:
            st.info("No explicit limitation sections identified in the retrieved excerpts.")
        for lim in limits:
            st.markdown(
                f"""
                <div class="sl-card">
                    <div class="sl-card-title">{lim.get('title')} — Page {lim.get('page_number')}</div>
                    <div class="sl-card-body">
                        <strong>Reported Limitation:</strong> {lim.get('limitation')}<br><br>
                        <div style="color:#94A3B8; font-style:italic; font-size:0.85rem; background:#0B0F17; padding:8px 12px; border-radius:4px; border:1px solid #1E293B;">
                            &ldquo;{lim.get('excerpt')}&rdquo;
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_patterns:
        for idx, pattern in enumerate(result.get("patterns", [])):
            st.markdown(
                f"""
                <div class="sl-card">
                    <div class="sl-card-title">Recurring Pattern #{idx + 1}</div>
                    <div class="sl-card-body">{pattern}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_exps:
        for idx, exp in enumerate(result.get("proposed_experiments", [])):
            st.markdown(
                f"""
                <div class="sl-card">
                    <div class="sl-card-title" style="color:#34D399;">Experiment Blueprint #{idx + 1}</div>
                    <div class="sl-card-body">{exp}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

prev_analyses = db.get_gap_analyses()
if prev_analyses:
    st.markdown("<hr style='margin: 1.5rem 0 1rem; border-color: #1E293B;'>", unsafe_allow_html=True)
    with st.expander(f"Historical Analyses ({len(prev_analyses)})"):
        for a in prev_analyses[:5]:
            st.markdown(f"- **{format_dt(a.get('created_at'))}** — {a.get('summary', '')[:110]}…")
