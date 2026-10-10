"""
pages/04_Research_Chat.py
Minimalist, Professional Research Document Chatbot.
Focused solely on uploading research papers and asking grounded questions with verified citations.
"""
from __future__ import annotations

from datetime import datetime
import streamlit as st

from database import db
from services.pdf_service import ingest_pdf
from services.retrieval_service import search_papers
from services.llm_service import generate_answer
from utils import config
from utils.helpers import truncate, clean_paper_title

# ── Header & Active Document Controls ──────────────────────────────────────────
ready_papers = db.get_papers_by_status("ready")

# If no papers uploaded, show centered upload experience
if not ready_papers:
    st.markdown(
        """
        <div style="text-align: center; margin: 3rem auto 1.5rem; max-width: 600px;">
            <div style="width: 48px; height: 48px; background: #1E1B4B; border: 1px solid #4F46E5; border-radius: 12px; margin: 0 auto 16px; display: flex; align-items: center; justify-content: center; font-size: 1.25rem; color: #818CF8; font-weight: 700;">
                SL
            </div>
            <div style="font-size: 1.4rem; font-weight: 700; color: #F8FAFC; margin-bottom: 8px;">
                Upload a Research Paper to Begin
            </div>
            <div style="font-size: 0.88rem; color: #94A3B8; line-height: 1.5; margin-bottom: 2rem;">
                Upload any PDF publication to chat, extract evidence, and ask grounded research questions.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        up_file = st.file_uploader("Upload PDF Document", type=["pdf"], key="empty_state_pdf_drop", label_visibility="collapsed")
        if up_file:
            with st.spinner("Analyzing and indexing publication..."):
                res = ingest_pdf(file_bytes=up_file.getvalue(), filename=up_file.name)
                if res["status"] in ("success", "duplicate"):
                    st.session_state["active_paper_id"] = res.get("paper_id")
                    st.toast(f"Document ready: {up_file.name}")
                    st.rerun()
                else:
                    st.error(res.get("message", "Error uploading document."))
    st.stop()

# ── Document Selection & Top Action Bar ────────────────────────────────────────
paper_options = {
    f"{clean_paper_title(p.get('title'), p.get('file_path'))} ({p.get('page_count', 1)} pages)": p["id"]
    for p in ready_papers
}

# Determine default paper index
active_paper_id = st.session_state.get("active_paper_id", ready_papers[0]["id"])
default_idx = 0
for idx, (label, pid) in enumerate(paper_options.items()):
    if pid == active_paper_id:
        default_idx = idx
        break

col_doc, col_up, col_new = st.columns([3.2, 0.9, 0.9], gap="small")

with col_doc:
    chosen_label = st.selectbox(
        "Active Paper",
        options=list(paper_options.keys()),
        index=default_idx,
        label_visibility="collapsed",
        help="Select which uploaded paper to query.",
    )
    selected_paper_id = paper_options[chosen_label]
    st.session_state["active_paper_id"] = selected_paper_id
    selected_paper = next((p for p in ready_papers if p["id"] == selected_paper_id), ready_papers[0])

# Session management
existing_sessions = db.get_chat_sessions()
if not existing_sessions:
    default_id = db.create_chat_session("Research Session", [selected_paper_id])
    st.session_state["active_session_id"] = default_id
elif "active_session_id" not in st.session_state:
    st.session_state["active_session_id"] = existing_sessions[0]["id"]

active_session_id = st.session_state["active_session_id"]

with col_up:
    with st.popover("+ Upload", use_container_width=True):
        st.markdown("**Upload Additional Paper**")
        pop_file = st.file_uploader("Select PDF", type=["pdf"], key="top_bar_pdf_uploader")
        if pop_file:
            with st.spinner("Indexing PDF..."):
                res = ingest_pdf(file_bytes=pop_file.getvalue(), filename=pop_file.name)
                if res["status"] in ("success", "duplicate"):
                    st.session_state["active_paper_id"] = res.get("paper_id")
                    st.toast(f"Ready: {pop_file.name}")
                    st.rerun()
                else:
                    st.error(res.get("message", "Ingestion failed."))
with col_new:
    if st.button("+ New Chat", key="btn_reset_chat", use_container_width=True):
        new_id = db.create_chat_session(f"Chat Session {len(existing_sessions) + 1}", [selected_paper_id])
        st.session_state["active_session_id"] = new_id
        st.rerun()

st.markdown("<hr style='margin: 0.5rem 0 1rem; border-color: #1E293B;'>", unsafe_allow_html=True)

# ── Message Stream ─────────────────────────────────────────────────────────────
messages = db.get_chat_messages(active_session_id)

# If no messages in this session, show a clean, minimal prompt welcome
if not messages:
    doc_title_clean = clean_paper_title(selected_paper.get("title"), selected_paper.get("file_path"))
    st.markdown(
        f"""
        <div style="text-align: center; margin: 2rem 0 1.5rem;">
            <div style="width: 40px; height: 40px; background: #1E1B4B; border: 1px solid #4F46E5; border-radius: 10px; margin: 0 auto 10px; display: flex; align-items: center; justify-content: center; font-size: 1rem; color: #818CF8; font-weight: 700;">
                SL
            </div>
            <div style="font-size: 1.25rem; font-weight: 700; color: #F8FAFC; margin-bottom: 4px;">
                Chat with {truncate(doc_title_clean, 60)}
            </div>
            <div style="font-size: 0.85rem; color: #94A3B8;">
                Ask any question grounded directly in the text and empirical findings of this paper.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Clean horizontal suggestion pills
    sc1, sc2, sc3, sc4 = st.columns(4)
    if sc1.button("Summarize Methodology", use_container_width=True, key="chip_method"):
        st.session_state["auto_query"] = "Summarize the core methodology, problem statement, and key contributions of this paper."
        st.rerun()
    if sc2.button("Author Limitations", use_container_width=True, key="chip_limits"):
        st.session_state["auto_query"] = "What explicit limitations, assumptions, and constraints did the authors identify?"
        st.rerun()
    if sc3.button("Datasets & Benchmarks", use_container_width=True, key="chip_data"):
        st.session_state["auto_query"] = "What evaluation datasets, metrics, and quantitative benchmark results were reported?"
        st.rerun()
    if sc4.button("Empirical Results", use_container_width=True, key="chip_results"):
        st.session_state["auto_query"] = "How do the empirical results in this paper compare against existing baseline approaches?"
        st.rerun()

# Render chat messages
for msg in messages:
    role = msg.get("role", "user")
    content = msg.get("content", "")
    citations = msg.get("citations") or []
    created_at = msg.get("created_at", "")
    time_str = ""
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            time_str = dt.strftime("%I:%M %p")
        except Exception:
            time_str = ""

    if role == "user":
        st.markdown(
            f"""
            <div class="chat-bubble-user">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 600; font-size: 0.82rem; color: #F8FAFC;">You</span>
                    <span style="font-size: 0.72rem; color: #64748B;">{time_str}</span>
                </div>
                <div style="font-size: 0.9rem; color: #F1F5F9; line-height: 1.55;">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div class="chat-bubble-ai">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 20px; height: 20px; background: #4F46E5; border-radius: 5px; color: #FFFFFF; font-weight: 700; font-size: 9px; display: flex; align-items: center; justify-content: center;">SL</div>
                        <span style="font-weight: 700; font-size: 0.85rem; color: #F8FAFC;">ScholarLens</span>
                        <span class="badge badge-ready" style="font-size: 0.65rem;">Grounded</span>
                    </div>
                    <span style="font-size: 0.72rem; color: #64748B;">{time_str}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(content)

        if citations:
            with st.expander(f"Evidence Sources ({len(citations)})", expanded=False):
                for idx, cit in enumerate(citations):
                    score_txt = f" · Similarity: {cit.get('score'):.2f}" if cit.get("score") is not None else ""
                    c_title = clean_paper_title(cit.get('title'))
                    st.markdown(
                        f"""
                        <div class="source-item">
                            <div style="font-weight: 600; color: #F8FAFC;">
                                [{idx + 1}] {c_title} — Page {cit.get('page_number')}{score_txt}
                            </div>
                            <div style="color: #94A3B8; font-style: italic; margin-top: 4px; font-size: 0.8rem; line-height: 1.45;">
                                &ldquo;{cit.get('excerpt')}&rdquo;
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

# Auto-heal: If the last message is an unanswered user query, synthesize response now
if messages and messages[-1]["role"] == "user":
    pending_query = messages[-1]["content"]
    with st.spinner("Synthesizing answer..."):
        retrieved = search_papers(
            query=pending_query,
            paper_ids=[selected_paper_id],
            top_k=config.TOP_K_RESULTS,
        )
        result = generate_answer(
            question=pending_query,
            retrieved_chunks=retrieved,
        )
        db.add_chat_message(active_session_id, "assistant", result["answer"], citations=result["citations"])
    st.rerun()

# ── Chat Input ─────────────────────────────────────────────────────────────────
user_query = st.chat_input("Ask a question about this research document...")
if not user_query and st.session_state.get("auto_query"):
    user_query = st.session_state.pop("auto_query")

if user_query:
    db.add_chat_message(active_session_id, "user", user_query)
    st.rerun()
