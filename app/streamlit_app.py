"""
DeepValue AI — Streamlit Dashboard

Main entry point.  Sidebar navigation to three views:
    1. Individual Analyzer — single ticker deep-dive
    2. S&P 500 Screener   — batch scan for opportunities
    3. Backtesting         — historical simulation with benchmark
"""

import sys
from pathlib import Path

# Ensure BOTH the project root (for `import core`) and the app directory
# (for `import page_*`) are on sys.path. This is needed because Streamlit
# Cloud runs from the repo root, not from inside app/.
_project_root = str(Path(__file__).resolve().parent.parent)
_app_dir = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

import streamlit as st  # noqa: E402
from theme import COLORS, inject_global_css  # noqa: E402

# ---------------------------------------------------------------------------
# Page configuration (MUST be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="DeepValue AI",
    page_icon="\U0001F4C8",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Dark fintech theme — fonts, cards, controls, Plotly template.
inject_global_css()

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.markdown(
    """
    <div class="dv-brand" style="padding-top:6px;">
        <div class="dv-logo">
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                 stroke="#04140a" stroke-width="2.4" stroke-linecap="round"
                 stroke-linejoin="round">
                <path d="M3 17l5-5 4 4 8-8"/>
                <path d="M16 8h4v4"/>
            </svg>
        </div>
        <div>
            <div class="dv-title" style="font-size:1.25rem;">DeepValue AI</div>
            <div class="dv-tag">ML investment intelligence</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(
    f'<div style="height:1px;background:{COLORS["border"]};margin:10px 0 16px 0;"></div>',
    unsafe_allow_html=True,
)

_PAGES = {
    "Individual Analyzer": "Single-ticker deep dive",
    "S&P 500 Screener": "Batch opportunity scan",
    "Backtesting": "Historical simulation",
}

st.sidebar.markdown(
    f'<div style="color:{COLORS["text_faint"]};font-size:0.72rem;'
    'text-transform:uppercase;letter-spacing:0.08em;font-weight:600;'
    'margin-bottom:6px;">Navigate</div>',
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    list(_PAGES.keys()),
    label_visibility="collapsed",
    captions=list(_PAGES.values()),
)

st.sidebar.markdown(
    f'<div style="height:1px;background:{COLORS["border"]};margin:18px 0 14px 0;"></div>',
    unsafe_allow_html=True,
)
st.sidebar.info(
    "Models are generated with **`make pipeline`**.\n\n"
    "Without trained models the app cannot generate predictions."
)
st.sidebar.markdown(
    f'<div style="position:relative;margin-top:18px;color:{COLORS["text_faint"]};'
    'font-size:0.72rem;">v1.0 · S&P 500 · 34 features</div>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------
if page == "Individual Analyzer":
    from page_analyzer import render
    render()
elif page == "S&P 500 Screener":
    from page_screener import render
    render()
else:
    from page_backtesting import render
    render()
