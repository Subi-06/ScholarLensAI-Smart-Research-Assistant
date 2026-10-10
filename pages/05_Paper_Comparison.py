"""
pages/05_Paper_Comparison.py
Structured multi-paper methodology and findings comparison dashboard.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd

from database import db
from services.comparison_service import compare_papers, ALL_DIMENSIONS

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Paper Comparison</div>
            <div class="sl-header-subtitle">Contrast research objectives, algorithms, benchmarks, evaluation metrics, and findings side by side</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ready_papers = db.get_papers_by_status("ready")
if len(ready_papers) < 2:
    st.markdown(
        """
        <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #334155;">
            <div style="font-weight: 600; color: #F8FAFC; margin-bottom: 4px;">Minimum 2 Documents Required</div>
            <div style="font-size: 0.85rem; color: #94A3B8;">
                At least 2 processed publications are required to synthesize a comparative matrix. Please ingest additional PDFs in the Paper Library.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.stop()

# ── Selection Form ─────────────────────────────────────────────────────────────
paper_map = {f"{p['title']} ({p.get('year') or 'N/A'})": p["id"] for p in ready_papers}

col_sel_p, col_sel_d = st.columns([1, 1])

with col_sel_p:
    selected_labels = st.multiselect(
        "Select documents to compare (2–6 recommended)",
        options=list(paper_map.keys()),
        default=list(paper_map.keys())[:min(3, len(paper_map))],
        help="Select 2 or more research documents to contrast.",
    )

with col_sel_d:
    selected_dims = st.multiselect(
        "Comparison dimensions",
        options=ALL_DIMENSIONS,
        default=[
            "Research Objective",
            "Algorithm / Method",
            "Dataset",
            "Key Findings",
            "Limitations",
        ],
        help="Select academic criteria to extract and contrast.",
    )

selected_ids = [paper_map[l] for l in selected_labels]

col_btn, _ = st.columns([1, 4])
btn_compare = col_btn.button("Generate Comparison Matrix", type="primary", disabled=(len(selected_ids) < 2))

if len(selected_ids) < 2:
    st.warning("Please select at least 2 documents to compare.")
    st.stop()

st.markdown("<hr style='margin: 1.25rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

comparison_key = f"comp_{'_'.join(str(i) for i in sorted(selected_ids))}_{'_'.join(selected_dims)}"

if btn_compare or ("active_comparison_df" in st.session_state and st.session_state.get("comparison_key") == comparison_key):
    if btn_compare:
        with st.spinner("Extracting comparative dimensions from research corpus..."):
            df = compare_papers(selected_ids, selected_dims)
            st.session_state["active_comparison_df"] = df
            st.session_state["comparison_key"] = comparison_key

    df: pd.DataFrame = st.session_state.get("active_comparison_df")

    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Comparative Matrix
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(
        df,
        use_container_width=True,
    )

    csv_bytes = df.to_csv().encode("utf-8")
    st.download_button(
        "Download Comparison Table (CSV)",
        data=csv_bytes,
        file_name="scholarlens_paper_comparison.csv",
        mime="text/csv",
    )

    st.markdown("<hr style='margin: 1.5rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Dimensional Breakdown
        </div>
        """,
        unsafe_allow_html=True,
    )
    for dim in selected_dims:
        with st.expander(dim, expanded=True):
            cols = st.columns(len(df.index))
            for i, paper_name in enumerate(df.index):
                with cols[i]:
                    st.markdown(
                        f"""
                        <div class="sl-card" style="height:100%;">
                            <div class="sl-card-title">{paper_name}</div>
                            <div class="sl-card-body">{df.loc[paper_name, dim]}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
