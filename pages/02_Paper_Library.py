"""
pages/02_Paper_Library.py
Upload PDFs, view metadata, processing status, inspect chunks, and manage papers.
Fully custom ingestion pipeline without LangChain.
"""
from __future__ import annotations

import streamlit as st
from database import db
from services.pdf_service import ingest_pdf
from utils.helpers import format_dt, truncate, human_size, clean_paper_title

# ── Header Bar ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="sl-header-bar">
        <div>
            <div class="sl-header-title">Paper Library</div>
            <div class="sl-header-subtitle">Ingest, extract, and inspect research documents for semantic retrieval and evidence analysis</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Upload Section ────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style="font-size: 1.05rem; font-weight: 700; color: #0F172A; margin-bottom: 0.5rem;">
        Document Ingestion
    </div>
    """,
    unsafe_allow_html=True,
)

with st.container():
    uploaded_files = st.file_uploader(
        "Upload PDF documents",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload single or multiple research papers. PyMuPDF extracts text per page with character boundary tracking.",
    )

    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} document(s) for ingestion.")
        if st.button("Process Documents", type="primary", key="btn_process_papers"):
            progress_bar = st.progress(0, text="Initiating ingestion pipeline...")
            results_summary = {"success": 0, "duplicate": 0, "error": 0}

            for idx, uploaded_file in enumerate(uploaded_files):
                progress_val = idx / len(uploaded_files)
                progress_bar.progress(
                    progress_val,
                    text=f"Extracting ({idx + 1}/{len(uploaded_files)}): {uploaded_file.name}",
                )

                file_bytes = uploaded_file.getvalue()
                res = ingest_pdf(file_bytes=file_bytes, filename=uploaded_file.name)

                if res["status"] == "success":
                    results_summary["success"] += 1
                    st.success(res["message"])
                elif res["status"] == "duplicate":
                    results_summary["duplicate"] += 1
                    st.info(res["message"])
                else:
                    results_summary["error"] += 1
                    st.error(res["message"])

            progress_bar.progress(1.0, text="Ingestion complete.")
            st.toast(
                f"Ingestion finished: {results_summary['success']} added, {results_summary['duplicate']} duplicates, {results_summary['error']} errors."
            )
            st.rerun()

st.markdown("<hr style='margin: 1.25rem 0 1.5rem; border-color: #1E293B;'>", unsafe_allow_html=True)

# ── Repository Overview & Filter ──────────────────────────────────────────────
all_papers = db.get_all_papers()
stats = db.get_stats()

st.markdown(
    """
    <div style="font-size: 1.05rem; font-weight: 700; color: #F8FAFC; margin-bottom: 0.75rem;">
        Document Repository
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
c1.metric("Total Documents", stats["total_papers"])
c2.metric("Ready for Retrieval", stats["processed_papers"])
c3.metric("Research Questions Asked", stats["questions_asked"])

if not all_papers:
    st.markdown(
        """
        <div class="sl-card" style="padding: 1.75rem; text-align: center; border-style: dashed; border-color: #334155; margin-top: 1rem;">
            <div style="font-weight: 600; color: #F8FAFC; margin-bottom: 4px;">No Documents in Repository</div>
            <div style="font-size: 0.85rem; color: #94A3B8;">
                Use the upload control above to ingest PDF research publications.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    col_search, col_status = st.columns([3, 1])
    search_query = col_search.text_input(
        "Search repository",
        placeholder="Filter by title, author, or keyword...",
        label_visibility="collapsed",
    )
    status_filter = col_status.selectbox(
        "Filter status",
        options=["All", "ready", "processing", "uploaded", "error"],
        label_visibility="collapsed",
    )

    filtered_papers = all_papers
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_papers = [
            p for p in filtered_papers
            if q in p.get("title", "").lower()
            or any(q in str(a).lower() for a in (p.get("authors") or []))
            or q in (p.get("abstract") or "").lower()
        ]

    if status_filter != "All":
        filtered_papers = [p for p in filtered_papers if p.get("status") == status_filter]

    st.caption(f"Displaying {len(filtered_papers)} of {len(all_papers)} documents")

    for paper in filtered_papers:
        paper_id = paper["id"]
        status = paper.get("status", "uploaded")
        badge_class = {
            "ready": "badge-ready",
            "processing": "badge-process",
            "uploaded": "badge-uploaded",
            "error": "badge-error",
        }.get(status, "badge-uploaded")

        authors_list = paper.get("authors") or []
        authors_display = ", ".join(authors_list) if authors_list else "Authors not specified"
        year_display = str(paper["year"]) if paper.get("year") else "N/A"

        header_title = f"{paper['title']} ({year_display})"

        with st.expander(f"{truncate(header_title, 85)}  [{status.upper()}]"):
            m1, m2, m3, m4 = st.columns(4)
            m1.markdown(f"**Status:** <span class='badge {badge_class}'>{status}</span>", unsafe_allow_html=True)
            m2.write(f"**Pages:** {paper.get('page_count', 0)}")
            m3.write(f"**Word Count:** {paper.get('word_count', 0):,}")
            m4.write(f"**Ingested:** {format_dt(paper.get('created_at'))}")

            st.write(f"**Authors:** {authors_display}")

            if paper.get("abstract"):
                st.markdown("**Abstract:**")
                st.markdown(
                    f"<div style='background:#111827; border:1px solid #1E293B; padding:12px; border-radius:6px; font-size:0.875rem; line-height:1.55; color:#CBD5E1;'>{paper['abstract']}</div>",
                    unsafe_allow_html=True,
                )

            if paper.get("error_msg"):
                st.error(f"Extraction error: {paper['error_msg']}")

            st.write("")

            act_col1, act_col2 = st.columns([1, 1])

            show_chunks = act_col1.checkbox(
                f"Inspect Text Chunks ({len(db.get_chunks(paper_id))})",
                key=f"chk_toggle_{paper_id}",
            )

            if act_col2.button("Delete Document", key=f"del_btn_{paper_id}", type="secondary"):
                db.delete_paper(paper_id, remove_file=True)
                st.success(f"Removed '{paper['title']}' from repository.")
                st.rerun()

            if show_chunks:
                chunks = db.get_chunks(paper_id)
                if not chunks:
                    st.info("No chunks indexed for this document.")
                else:
                    st.markdown(f"#### Chunk Inspection ({len(chunks)} total)")
                    chunk_page = st.number_input(
                        f"Chunk index (0 to {len(chunks)-1})",
                        min_value=0,
                        max_value=max(0, len(chunks) - 1),
                        value=0,
                        step=1,
                        key=f"chunk_nav_{paper_id}",
                    )
                    selected_chunk = chunks[chunk_page]

                    st.markdown(
                        f"""
                        <div style="background:#111827; border:1px solid #1E293B; border-radius:6px; padding:12px; font-size:0.85rem; margin-top:8px;">
                            <div style="font-weight:600; color:#F8FAFC; margin-bottom:6px;">
                                Chunk #{selected_chunk['chunk_index']} &nbsp;·&nbsp;
                                Page {selected_chunk['page_number']} &nbsp;·&nbsp;
                                Characters {selected_chunk['char_start']}–{selected_chunk['char_end']} ({len(selected_chunk['text'])} chars)
                            </div>
                            <div style="color:#CBD5E1; white-space:pre-wrap; font-family:monospace; background:#0B0F17; padding:10px; border-radius:4px; border:1px solid #1E293B; font-size:0.82rem;">{selected_chunk['text']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
