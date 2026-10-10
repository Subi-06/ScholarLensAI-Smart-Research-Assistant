"""
pages/07_Paper_Discovery.py
External academic discovery engine querying Semantic Scholar and arXiv APIs.
Live, authentic paper metadata and direct links.
"""
from __future__ import annotations

import streamlit as st
from services.paper_search import discover_papers
from utils.helpers import truncate

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Paper Search</div>
            <div class="sl-header-subtitle">Search Springer, IEEE, arXiv, and Semantic Scholar for state-of-the-art scientific literature</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── State Initialization ───────────────────────────────────────────────────────
if "disc_page_query" not in st.session_state:
    st.session_state["disc_page_query"] = ""

# Trending topic buttons above form
st.markdown(
    """
    <div style="display: flex; align-items: center; gap: 8px; margin: 0 0 10px;">
        <span style="font-size: 0.78rem; font-weight: 600; color: #64748B; text-transform: uppercase;">Trending Topics:</span>
    </div>
    """,
    unsafe_allow_html=True,
)
col_t1, col_t2, col_t3 = st.columns(3)
trigger_search = False
if col_t1.button("Retrieval-Augmented Generation", key="topic_rag", use_container_width=True):
    st.session_state["disc_page_query"] = "Retrieval Augmented Generation"
    trigger_search = True
if col_t2.button("Vision Transformer Architectures", key="topic_vit", use_container_width=True):
    st.session_state["disc_page_query"] = "Vision Transformer Survey"
    trigger_search = True
if col_t3.button("Smart Grid Cybersecurity AI", key="topic_slr", use_container_width=True):
    st.session_state["disc_page_query"] = "Smart Grid Cybersecurity"
    trigger_search = True

# ── Search Form ────────────────────────────────────────────────────────────────
with st.form("paper_discovery_form", clear_on_submit=False):
    col_q, col_src, col_lim = st.columns([3, 1, 1])

    search_query = col_q.text_input(
        "Academic Search Query",
        value=st.session_state.get("disc_page_query", ""),
        placeholder="e.g. smart grid cybersecurity or vision transformer",
        label_visibility="collapsed",
    )
    source_choice = col_src.selectbox(
        "Index Source",
        options=["All Sources", "IEEE", "Springer", "arXiv", "Semantic Scholar"],
        label_visibility="collapsed",
    )
    limit_choice = col_lim.slider(
        "Max results",
        min_value=5,
        max_value=30,
        value=12,
        step=5,
        label_visibility="collapsed",
    )

    btn_search = st.form_submit_button("Search Literature", type="primary", use_container_width=True)

st.markdown("<hr style='margin: 1rem 0 1.5rem; border-color: #E2E8F0;'>", unsafe_allow_html=True)

# ── Search Results ────────────────────────────────────────────────────────────
active_query = search_query.strip() if search_query else st.session_state.get("disc_page_query", "").strip()

if (btn_search or trigger_search) and active_query:
    with st.spinner(f"Querying scientific indexes for '{active_query}'..."):
        results = discover_papers(active_query, source=source_choice, limit=limit_choice)
        st.session_state["discovery_results"] = results
        st.session_state["last_disc_query"] = active_query

results = st.session_state.get("discovery_results", [])
last_query = st.session_state.get("last_disc_query", "")

if results:
    st.markdown(
        f"""
        <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
            Results for <i>"{last_query}"</i> ({len(results)} publications found)
        </div>
        """,
        unsafe_allow_html=True,
    )

    for idx, paper in enumerate(results):
        src = paper.get("source", "Web")
        authors = ", ".join(paper.get("authors") or []) or "Authors not listed"
        year_str = str(paper.get("year")) if paper.get("year") else "N/A"
        cits = paper.get("citation_count")
        cit_str = f" · Cited by {cits:,}" if cits is not None else ""
        url = paper.get("url")

        st.markdown(
            f"""
            <div class="sl-card" style="border: 1px solid #1E293B; background: #111827; padding: 1.15rem 1.35rem; margin-bottom: 0.85rem;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div style="font-size: 1rem; font-weight: 600; color: #F8FAFC;">
                        <a href="{url}" target="_blank" style="text-decoration:none; color: #F8FAFC;">
                            {paper['title']}
                        </a>
                    </div>
                    <span class="badge" style="color: #C7D2FE; border-color: #4338CA; background: #1E1B4B;">
                        {src}
                    </span>
                </div>
                <div style="color:#64748B; font-size:0.8rem; margin-top:4px;">
                    {authors} &nbsp;·&nbsp; {year_str}{cit_str}
                </div>
                <div class="sl-card-body" style="margin-top:8px; color: #94A3B8;">
                    {truncate(paper.get('abstract', ''), 340)}
                </div>
                <div style="margin-top:12px; display: flex; gap: 8px;">
                    <a href="{url}" target="_blank" style="display:inline-block; font-size:0.8rem; font-weight:600; color:#818CF8; text-decoration:none; background:#1E1B4B; padding:5px 12px; border-radius:6px; border:1px solid #4338CA;">
                        Open Paper &rarr;
                    </a>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

elif (btn_search or trigger_search) and not results:
    st.warning(f"No records found for query '{active_query}'. Try modifying the keywords or selecting 'All Sources'.")
else:
    st.markdown(
        """
        <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #CBD5E1;">
            <div style="font-weight: 600; color: #0F172A; margin-bottom: 4px;">Search Academic Literature</div>
            <div style="font-size: 0.85rem; color: #64748B;">
                Enter a research query above or pick a trending topic to query IEEE, Springer Nature, arXiv, and Semantic Scholar.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
