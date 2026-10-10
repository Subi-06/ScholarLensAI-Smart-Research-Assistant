"""
app.py
ScholarLens AI — Academic Research Intelligence Platform.
Professional modern navigation shell matching the reference design.
"""
from __future__ import annotations

import streamlit as st
from database.db import init_db, get_stats

# ── One-time DB initialisation ─────────────────────────────────────────────────
init_db()

# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="ScholarLens AI — Research Assistant",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Built-in Brand Logo (Placed at the very top of sidebar above navigation) ───
st.logo("assets/logo.svg", icon_image="assets/icon.svg")

# ── Global Design System & CSS ────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    color: #F8FAFC;
}

.stApp {
    background-color: #0B0F17 !important;
    color: #F8FAFC !important;
}

/* ── Full Page Scrolling & Background Fixes ────────────────────────────────── */
[data-testid="stAppViewContainer"] {
    background-color: #0B0F17 !important;
    overflow-y: auto !important;
    height: 100vh !important;
}

[data-testid="stMain"] {
    background-color: #0B0F17 !important;
    overflow-y: visible !important;
}

/* Header bar transparency */
header[data-testid="stHeader"] {
    background: transparent !important;
    height: 3.5rem !important;
    z-index: 10 !important;
}

/* Proper padding-top so headers are never cut off */
.block-container {
    max-width: 1480px;
    padding-top: 4.5rem !important;
    padding-bottom: 5rem !important;
    padding-left: 2.5rem !important;
    padding-right: 2.5rem !important;
}

/* Custom Sleek Dark Scrollbars */
::-webkit-scrollbar {
    width: 7px;
    height: 7px;
}

::-webkit-scrollbar-track {
    background: #0B0F17;
}

::-webkit-scrollbar-thumb {
    background: #1E293B;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: #334155;
}

/* ── Left Sidebar (Stealth Pure Black #06090F) ────────────────────────────── */
[data-testid="stSidebar"] {
    background-color: #06090F !important;
    border-right: 1px solid #1E293B !important;
}

[data-testid="stSidebarContent"] {
    background-color: #06090F !important;
    overflow-y: auto !important;
}

[data-testid="stSidebar"] * {
    color: #94A3B8 !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: #F8FAFC !important;
    font-weight: 600;
}

[data-testid="stSidebar"] hr {
    border-color: #1E293B !important;
}

/* Sidebar Nav Items */
[data-testid="stSidebarNavLink"] {
    border-radius: 6px;
    margin: 2px 0;
    padding: 0.45rem 0.75rem;
    transition: all 0.15s ease;
}

[data-testid="stSidebarNavLink"]:hover {
    background-color: #111827 !important;
}

[data-testid="stSidebarNavLink"]:hover * {
    color: #F8FAFC !important;
}

/* Active navigation link */
[data-testid="stSidebarNavLink"][aria-current="page"] {
    background-color: #111827 !important;
    border-left: 3px solid #6366F1 !important;
    border-radius: 6px;
}

[data-testid="stSidebarNavLink"][aria-current="page"] * {
    color: #FFFFFF !important;
    font-weight: 600;
}

/* ── Top Header Component ────────────────────────────────────────────────── */
.sl-header-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 1rem;
    margin-bottom: 1.25rem;
    border-bottom: 1px solid #1E293B;
}

.sl-header-title {
    font-size: 1.5rem;
    font-weight: 700;
    color: #F8FAFC;
    letter-spacing: -0.02em;
    line-height: 1.2;
}

.sl-header-subtitle {
    font-size: 0.85rem;
    color: #94A3B8;
    margin-top: 3px;
}

/* ── Buttons ─────────────────────────────────────────────────────────────── */
div.stButton > button {
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.85rem;
    transition: all 0.15s ease-in-out;
    background-color: #111827 !important;
    color: #F8FAFC !important;
    border: 1px solid #1E293B !important;
}

div.stButton > button:hover {
    background-color: #1E293B !important;
    border-color: #6366F1 !important;
    color: #FFFFFF !important;
}

div.stButton > button[kind="primary"] {
    background-color: #4F46E5 !important;
    color: #FFFFFF !important;
    border: 1px solid #4F46E5 !important;
}

div.stButton > button[kind="primary"]:hover {
    background-color: #4338CA !important;
    border-color: #4338CA !important;
}

/* ── Cards & Containers ──────────────────────────────────────────────────── */
.sl-card {
    background-color: #111827 !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px;
    padding: 1.15rem 1.35rem;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
    margin-bottom: 0.85rem;
    color: #F8FAFC !important;
}

.sl-card-title {
    font-size: 0.95rem;
    font-weight: 600;
    color: #F8FAFC;
    margin-bottom: 0.35rem;
}

.sl-card-body {
    color: #94A3B8;
    font-size: 0.85rem;
    line-height: 1.55;
}

/* ── Badges & Tags ───────────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    border: 1px solid transparent;
}

.badge-ready {
    background-color: #064E3B;
    color: #A7F3D0;
    border-color: #047857;
}

.badge-process {
    background-color: #78350F;
    color: #FDE68A;
    border-color: #B45309;
}

.badge-uploaded {
    background-color: #1E293B;
    color: #94A3B8;
    border-color: #334155;
}

.badge-error {
    background-color: #7F1D1D;
    color: #FECACA;
    border-color: #B91C1C;
}

.tag-pill {
    display: inline-block;
    background: #1E1B4B;
    color: #C7D2FE;
    border: 1px solid #4338CA;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 0.72rem;
    font-weight: 600;
    margin-right: 5px;
    margin-top: 4px;
}

/* ── Metric cards ────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background-color: #111827 !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px;
    padding: 1rem 1.25rem;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

[data-testid="stMetricValue"] {
    color: #F8FAFC !important;
    font-size: 1.75rem;
    font-weight: 700;
}

/* ── Form Controls, Inputs & Selectbox Overrides ─────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
[data-testid="stNumberInput"] input {
    background-color: #111827 !important;
    border: 1px solid #1E293B !important;
    color: #F8FAFC !important;
    border-radius: 6px !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div:focus {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 1px #6366F1 !important;
}

/* BaseWeb Dropdown Menu in Dark Mode */
[data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul {
    background-color: #111827 !important;
    border: 1px solid #1E293B !important;
}

[data-baseweb="menu"] li, [data-baseweb="menu"] div {
    color: #F8FAFC !important;
}

[data-baseweb="menu"] li:hover {
    background-color: #1E293B !important;
}

/* ── Bottom Fixed Container (Fix for Streamlit white bottom bar!) ────────── */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"],
.stChatFloatingInputContainer {
    background-color: #0B0F17 !important;
    background: #0B0F17 !important;
    border-top: 1px solid #1E293B !important;
}

/* ── Chat Input (Clean Dark Style with non-white typed letter color) ─────── */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] div {
    background-color: #111827 !important;
    background: #111827 !important;
}

[data-testid="stChatInput"] {
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"]:focus-within,
[data-testid="stChatInput"]:focus-within > div,
[data-testid="stChatInput"]:focus-within [data-baseweb="base-input"] {
    border-color: #6366F1 !important;
    box-shadow: 0 0 0 1px #6366F1 !important;
}

[data-testid="stChatInput"] textarea {
    background-color: transparent !important;
    color: #A5B4FC !important;
    caret-color: #818CF8 !important;
    font-size: 0.95rem !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: #64748B !important;
}

[data-testid="stChatInput"] button {
    background-color: #4F46E5 !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    border: none !important;
}

/* ── Chat Messages & Sources Styling (Dark Mode) ─────────────────────────── */
.chat-bubble-user {
    background: #1E293B !important;
    border: 1px solid #334155 !important;
    border-radius: 14px 14px 4px 14px !important;
    padding: 12px 18px !important;
    margin-bottom: 12px !important;
    color: #F8FAFC !important;
}

.chat-bubble-user * {
    color: #F8FAFC !important;
}

.chat-bubble-ai {
    background: #111827 !important;
    border: 1px solid #1E293B !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
    margin-bottom: 14px !important;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35) !important;
    color: #F8FAFC !important;
}

.chat-bubble-ai * {
    color: #F8FAFC;
}

.source-item {
    background: #0B1120 !important;
    border: 1px solid #1E293B !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
    margin-bottom: 6px !important;
    color: #94A3B8 !important;
}

/* Expander in Dark Mode */
[data-testid="stExpander"] {
    background-color: #111827 !important;
    border: 1px solid #1E293B !important;
    border-radius: 8px !important;
}

[data-testid="stExpander"] details {
    background-color: #111827 !important;
}

[data-testid="stExpander"] summary {
    color: #E2E8F0 !important;
}

/* Horizontal rule */
hr {
    border-color: #1E293B !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Navigation Pages (Strictly ordered to match reference UI) ────────────────
dashboard  = st.Page("pages/01_Dashboard.py",        title="Dashboard", default=True)
chat       = st.Page("pages/04_Research_Chat.py",    title="Research Chat")
search     = st.Page("pages/07_Paper_Discovery.py",  title="Paper Search")
library    = st.Page("pages/02_Paper_Library.py",    title="Paper Library")
comparison = st.Page("pages/05_Paper_Comparison.py", title="Paper Comparison")
gaps       = st.Page("pages/06_Research_Gaps.py",    title="Research Gaps")
screening  = st.Page("pages/03_AI_Screening.py",     title="AI Screening")
reports    = st.Page("pages/08_Reports.py",          title="Reports")

pg = st.navigation(
    [
        dashboard,
        chat,
        search,
        library,
        comparison,
        gaps,
        screening,
        reports,
    ]
)

# ── Sidebar Bottom Storage Meter & Settings Action ────────────────────────────
stats = get_stats()
total_papers = stats.get("total_papers", 0)
storage_pct = min(int((total_papers / 50.0) * 100), 100)

with st.sidebar:
    st.markdown("<div style='height: 2.5rem;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style="padding: 0.75rem 0.5rem; border-top: 1px solid #1E293B; margin-top: auto;">
            <div style="display: flex; justify-content: space-between; font-size: 0.75rem; font-weight: 500; color: #94A3B8; margin-bottom: 6px;">
                <span>Storage</span>
                <span style="color: #F8FAFC; font-weight: 600;">{total_papers}/50 papers</span>
            </div>
            <div style="background: #1E293B; border-radius: 9999px; height: 5px; overflow: hidden; width: 100%; margin-bottom: 12px;">
                <div style="background: #6366F1; width: {max(storage_pct, 4)}%; height: 100%; border-radius: 9999px;"></div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px; color: #94A3B8; font-size: 0.8rem; cursor: pointer; padding: 4px 0;">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                <span>Settings</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

pg.run()
