"""Shared visual theme for the DeepValue AI dashboard.

Single source of truth for the dark "fintech" look used across all pages:
    - Color tokens (COLORS)
    - Global CSS injection (inject_global_css) — fonts, cards, controls
    - A Plotly template (apply_plotly_theme / PLOTLY_LAYOUT) so every chart
      matches the dark surfaces instead of Plotly's white default
    - Small render helpers (metric_card, signal_banner, section_title)

Design system (generated for a fintech ML dashboard):
    Style       Dark Mode (OLED) — deep navy/black, high contrast
    Typography  IBM Plex Sans (UI) + IBM Plex Mono (numbers)
    Accent      #22C55E green for positive / BUY, #EF4444 red for negative
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# ---------------------------------------------------------------------------
# Color tokens — referenced by every page and chart. Change here, change
# everywhere. Names describe ROLE, not hue, so the palette can be retuned.
# ---------------------------------------------------------------------------
COLORS = {
    "bg": "#020617",          # app canvas (deepest)
    "surface": "#0B1220",     # cards / panels
    "surface_2": "#0F172A",   # raised surfaces, sidebar, inputs
    "border": "#1E293B",      # hairline borders
    "border_soft": "#172033",  # even subtler dividers
    "text": "#F8FAFC",        # primary text
    "text_muted": "#94A3B8",  # secondary / labels
    "text_faint": "#64748B",  # captions
    "primary": "#3B82F6",     # neutral accent (price lines, info)
    "positive": "#22C55E",    # BUY / gains / up
    "positive_dim": "#16A34A",
    "negative": "#EF4444",    # SELL / losses / down
    "negative_dim": "#DC2626",
    "warning": "#F59E0B",     # caution / thresholds
    "purple": "#A855F7",      # secondary series
    "teal": "#2DD4BF",        # tertiary series
    "bull": "#26A69A",        # candlestick up (chart standard)
    "bear": "#EF5350",        # candlestick down (chart standard)
}

# Sequential/divergent scales for heatmaps (red → neutral → green).
DIVERGENT_SCALE = [
    [0.0, "#7F1D1D"],
    [0.25, "#EF4444"],
    [0.5, "#0F172A"],
    [0.75, "#22C55E"],
    [1.0, "#14532D"],
]

FONT_FAMILY = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"
MONO_FAMILY = "'IBM Plex Mono', 'SF Mono', 'Roboto Mono', monospace"


# ---------------------------------------------------------------------------
# Global CSS — injected once per page via inject_global_css().
# ---------------------------------------------------------------------------
def _global_css() -> str:
    c = COLORS
    return f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

    /* ---- Base ---- */
    html, body, [class*="css"], .stApp {{
        font-family: {FONT_FAMILY};
        color: {c["text"]};
    }}
    .stApp {{
        background:
            radial-gradient(1200px 600px at 15% -10%, #0b1b3a 0%, transparent 55%),
            radial-gradient(1000px 500px at 100% 0%, #0a1f33 0%, transparent 50%),
            {c["bg"]};
        background-attachment: fixed;
    }}

    /* Tighten the default top padding so the custom header sits high */
    .block-container {{
        padding-top: 2.2rem;
        padding-bottom: 3rem;
        max-width: 1280px;
    }}

    /* ---- Headings ---- */
    h1, h2, h3, h4 {{
        font-family: {FONT_FAMILY};
        font-weight: 600;
        letter-spacing: -0.01em;
        color: {c["text"]};
    }}
    h1 {{ font-weight: 700; letter-spacing: -0.02em; }}

    /* Numbers feel deliberate in a tabular/mono face */
    [data-testid="stMetricValue"], .dv-mono {{
        font-family: {MONO_FAMILY};
        font-variant-numeric: tabular-nums;
    }}

    /* ---- Sidebar ---- */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {c["surface_2"]} 0%, {c["surface"]} 100%);
        border-right: 1px solid {c["border"]};
    }}
    [data-testid="stSidebar"] .stRadio > label {{
        color: {c["text_muted"]};
    }}

    /* ---- Native metric cards (st.metric) ---- */
    [data-testid="stMetric"] {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 14px;
        padding: 16px 18px;
        transition: border-color .2s ease, transform .2s ease;
    }}
    [data-testid="stMetric"]:hover {{
        border-color: #2b3b55;
        transform: translateY(-1px);
    }}
    [data-testid="stMetricLabel"] {{
        color: {c["text_muted"]};
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.45rem;
        font-weight: 600;
    }}

    /* ---- Buttons ---- */
    .stButton > button, .stDownloadButton > button {{
        border-radius: 10px;
        font-weight: 600;
        letter-spacing: 0.01em;
        border: 1px solid {c["border"]};
        transition: transform .15s ease, box-shadow .2s ease, background .2s ease;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(180deg, {c["positive"]} 0%, {c["positive_dim"]} 100%);
        color: #04140a;
        border: none;
        box-shadow: 0 1px 0 rgba(255,255,255,.15) inset, 0 8px 20px -8px rgba(34,197,94,.6);
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px);
        box-shadow: 0 1px 0 rgba(255,255,255,.2) inset, 0 12px 26px -8px rgba(34,197,94,.7);
    }}
    .stButton > button:focus-visible, .stDownloadButton > button:focus-visible {{
        outline: 2px solid {c["primary"]};
        outline-offset: 2px;
    }}

    /* ---- Inputs ---- */
    .stTextInput input, .stNumberInput input, .stDateInput input,
    [data-baseweb="select"] > div {{
        background: {c["surface_2"]} !important;
        border: 1px solid {c["border"]} !important;
        border-radius: 10px !important;
        color: {c["text"]} !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus {{
        border-color: {c["primary"]} !important;
    }}

    /* ---- Tables / dataframes ---- */
    [data-testid="stDataFrame"] {{
        border: 1px solid {c["border"]};
        border-radius: 14px;
        overflow: hidden;
    }}

    /* ---- Expander ---- */
    [data-testid="stExpander"] {{
        border: 1px solid {c["border"]};
        border-radius: 14px;
        background: {c["surface"]};
    }}

    /* ---- Alerts: soften the default chunky look ---- */
    [data-testid="stAlert"] {{
        border-radius: 12px;
        border: 1px solid {c["border"]};
    }}

    /* ---- Custom cards (rendered via helpers below) ---- */
    .dv-card {{
        background: {c["surface"]};
        border: 1px solid {c["border"]};
        border-radius: 16px;
        padding: 18px 20px;
        height: 100%;
    }}
    .dv-card .dv-label {{
        color: {c["text_muted"]};
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 500;
        margin: 0 0 6px 0;
    }}
    .dv-card .dv-value {{
        font-family: {MONO_FAMILY};
        font-variant-numeric: tabular-nums;
        font-size: 1.5rem;
        font-weight: 600;
        line-height: 1.1;
        color: {c["text"]};
    }}
    .dv-card .dv-sub {{
        font-size: 0.78rem;
        color: {c["text_faint"]};
        margin-top: 4px;
    }}

    /* Section title with accent rule */
    .dv-section {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.4rem 0 0.6rem 0;
    }}
    .dv-section .dv-bar {{
        width: 3px; height: 18px; border-radius: 2px;
        background: linear-gradient(180deg, {c["primary"]}, {c["positive"]});
    }}
    .dv-section h3 {{ margin: 0; font-size: 1.05rem; }}

    /* App brand header */
    .dv-brand {{
        display: flex; align-items: center; gap: 14px;
        padding: 2px 0 14px 0;
    }}
    .dv-brand .dv-logo {{
        width: 42px; height: 42px; border-radius: 12px;
        display: grid; place-items: center;
        background: linear-gradient(135deg, {c["primary"]} 0%, {c["positive"]} 100%);
        box-shadow: 0 8px 22px -8px rgba(34,197,94,.55);
    }}
    .dv-brand .dv-title {{
        font-size: 1.55rem; font-weight: 700; line-height: 1; letter-spacing: -0.02em;
    }}
    .dv-brand .dv-tag {{ color: {c["text_muted"]}; font-size: 0.82rem; margin-top: 3px; }}

    /* Pill / badge */
    .dv-pill {{
        display: inline-flex; align-items: center; gap: 6px;
        padding: 3px 10px; border-radius: 999px;
        font-size: 0.72rem; font-weight: 600; letter-spacing: 0.02em;
        border: 1px solid {c["border"]};
    }}

    @media (prefers-reduced-motion: reduce) {{
        * {{ transition: none !important; animation: none !important; }}
    }}
    </style>
    """


def inject_global_css() -> None:
    """Inject the global stylesheet. Safe to call once per page render."""
    st.markdown(_global_css(), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Plotly theme — registered as a named template and set as default so every
# figure inherits dark surfaces, the IBM Plex font, and subtle gridlines.
# ---------------------------------------------------------------------------
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family=FONT_FAMILY, color=COLORS["text"], size=13),
    colorway=[
        COLORS["primary"], COLORS["positive"], COLORS["warning"],
        COLORS["purple"], COLORS["teal"], COLORS["negative"],
    ],
    xaxis=dict(
        gridcolor=COLORS["border_soft"],
        zerolinecolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(color=COLORS["text_muted"], size=11),
        title_font=dict(color=COLORS["text_muted"], size=12),
    ),
    yaxis=dict(
        gridcolor=COLORS["border_soft"],
        zerolinecolor=COLORS["border"],
        linecolor=COLORS["border"],
        tickfont=dict(color=COLORS["text_muted"], size=11),
        title_font=dict(color=COLORS["text_muted"], size=12),
    ),
    legend=dict(
        bgcolor="rgba(11,18,32,0.6)",
        bordercolor=COLORS["border"],
        borderwidth=1,
        font=dict(color=COLORS["text"], size=11),
    ),
    hoverlabel=dict(
        bgcolor=COLORS["surface_2"],
        bordercolor=COLORS["border"],
        font=dict(family=MONO_FAMILY, color=COLORS["text"], size=12),
    ),
    margin=dict(t=30, b=40, l=10, r=10),
)

_dv_template = go.layout.Template(layout=PLOTLY_LAYOUT)
pio.templates["deepvalue"] = _dv_template


def apply_plotly_theme(fig: go.Figure, **layout_overrides) -> go.Figure:
    """Apply the dark DeepValue template to *fig* plus any per-chart overrides."""
    fig.update_layout(template="deepvalue", **layout_overrides)
    return fig


# ---------------------------------------------------------------------------
# Render helpers — used by pages for consistent custom cards/headers.
# ---------------------------------------------------------------------------
def section_title(text: str) -> None:
    """A heading with a small gradient accent bar (replaces st.subheader)."""
    st.markdown(
        f'<div class="dv-section"><span class="dv-bar"></span><h3>{text}</h3></div>',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, sub: str = "", accent: str | None = None) -> str:
    """Return HTML for a single custom metric card.

    Render several at once by joining the strings inside one st.markdown call
    wrapped in a fl/grid container — see metric_row().
    """
    border = f"border-left:3px solid {accent};" if accent else ""
    sub_html = f'<div class="dv-sub">{sub}</div>' if sub else ""
    return (
        f'<div class="dv-card" style="{border}">'
        f'<div class="dv-label">{label}</div>'
        f'<div class="dv-value">{value}</div>'
        f"{sub_html}</div>"
    )


def metric_row(cards: list[str], min_width: int = 150) -> None:
    """Render a responsive grid of metric_card() HTML strings."""
    grid = (
        f'<div style="display:grid;gap:14px;'
        f'grid-template-columns:repeat(auto-fit,minmax({min_width}px,1fr));'
        f'margin:6px 0 4px 0;">' + "".join(cards) + "</div>"
    )
    st.markdown(grid, unsafe_allow_html=True)
