"""
pages/08_Reports.py
Academic literature report generation and export dashboard.
Generate and download literature surveys, comparison tables, evidence tables, and research-gap reports.
"""
from __future__ import annotations

import streamlit as st
from database import db
from services.gap_analysis import analyse_gaps
from services.report_service import (
    generate_literature_survey,
    generate_comparison_report,
    generate_gap_report,
    generate_evidence_table_report,
    save_report,
)
from utils.helpers import timestamp_str

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Reports & Synthesis</div>
            <div class="sl-header-subtitle">Compile publication-grade literature surveys, comparative analyses, evidence tables, and gap blueprints</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ready_papers = db.get_papers_by_status("ready")
if not ready_papers:
    st.markdown(
        """
        <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #334155;">
            <div style="font-weight: 600; color: #F8FAFC; margin-bottom: 4px;">No Publications Available</div>
            <div style="font-size: 0.85rem; color: #94A3B8;">
                Please upload PDF research publications in the Paper Library before compiling synthesis reports.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Select Documents for Report Scope ─────────────────────────────────────────
paper_map = {f"{p['title']} ({p.get('year') or 'N/A'})": p["id"] for p in ready_papers}

st.markdown(
    """
    <div style="font-size: 1rem; font-weight: 600; color: #F8FAFC; margin-bottom: 0.5rem;">
        Target Document Scope
    </div>
    """,
    unsafe_allow_html=True,
)
selected_labels = st.multiselect(
    "Select Documents to Include",
    options=list(paper_map.keys()),
    default=list(paper_map.keys()),
    help="Selected documents will be synthesized in the compiled report.",
    label_visibility="collapsed",
)
selected_ids = [paper_map[l] for l in selected_labels]

if not selected_ids:
    st.warning("Please select at least one document for report compilation.")
    st.stop()

st.markdown("<hr style='margin: 1.25rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

# ── Report Generation Tabs ─────────────────────────────────────────────────────
tab_survey, tab_comp, tab_gaps, tab_evid = st.tabs(
    [
        "Literature Survey",
        "Comparative Matrix Report",
        "Research Gaps Report",
        "Evidence Table",
    ]
)

# 1. Literature Survey
with tab_survey:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">
            Evidence-Backed Literature Survey
        </div>
        """,
        unsafe_allow_html=True,
    )
    survey_topic = st.text_input("Survey Title / Subject Area", value="Academic Literature Survey: State of the Art")
    if st.button("Generate Literature Survey", type="primary", key="btn_gen_survey"):
        with st.spinner("Compiling multi-document literature survey..."):
            md_content = generate_literature_survey(selected_ids, topic=survey_topic)
            save_report(md_content, f"literature_survey_{timestamp_str()}.md")
            st.session_state["active_report_md"] = md_content
            st.session_state["report_filename"] = "ScholarLens_Literature_Survey.md"

# 2. Comparative Matrix Report
with tab_comp:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">
            Cross-Document Comparison Report
        </div>
        """,
        unsafe_allow_html=True,
    )
    if len(selected_ids) < 2:
        st.info("Select at least 2 documents to compile a comparative report.")
    else:
        if st.button("Generate Comparison Report", type="primary", key="btn_gen_comp"):
            with st.spinner("Extracting comparative dimensions across corpus..."):
                md_content = generate_comparison_report(selected_ids)
                save_report(md_content, f"comparison_report_{timestamp_str()}.md")
                st.session_state["active_report_md"] = md_content
                st.session_state["report_filename"] = "ScholarLens_Comparison_Report.md"

# 3. Research Gaps Report
with tab_gaps:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">
            Research Gaps & Novelty Blueprint
        </div>
        """,
        unsafe_allow_html=True,
    )
    gap_focus = st.text_input("Optional Domain Focus", placeholder="e.g. Robustness and Parameter Efficiency", key="rep_gap_focus")
    if len(selected_ids) < 2:
        st.info("Select at least 2 documents for research-gap synthesis.")
    else:
        if st.button("Generate Research Gap Report", type="primary", key="btn_gen_gaps"):
            with st.spinner("Synthesizing limitations and formulating novel experiments..."):
                analysis = analyse_gaps(selected_ids, focus=gap_focus)
                md_content = generate_gap_report(analysis)
                save_report(md_content, f"research_gaps_{timestamp_str()}.md")
                st.session_state["active_report_md"] = md_content
                st.session_state["report_filename"] = "ScholarLens_Research_Gaps_Report.md"

# 4. Evidence Table Report
with tab_evid:
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.5rem;">
            Structured Evidence Table
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Generate Evidence Table", type="primary", key="btn_gen_evid"):
        with st.spinner("Compiling grounded evidence table..."):
            md_content = generate_evidence_table_report(selected_ids)
            save_report(md_content, f"evidence_table_{timestamp_str()}.md")
            st.session_state["active_report_md"] = md_content
            st.session_state["report_filename"] = "ScholarLens_Evidence_Table.md"

# ── Preview & Download Section ─────────────────────────────────────────────────
if "active_report_md" in st.session_state:
    st.markdown("<hr style='margin: 1.5rem 0 1.25rem; border-color: #1E293B;'>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Report Preview & Export
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_down, col_copy = st.columns([1, 4])
    report_text = st.session_state["active_report_md"]
    file_name = st.session_state.get("report_filename", "ScholarLens_Report.md")

    col_down.download_button(
        "Download Markdown Document",
        data=report_text.encode("utf-8"),
        file_name=file_name,
        mime="text/markdown",
        type="primary",
    )

    with st.expander("Live Document Preview", expanded=True):
        st.markdown(report_text)
