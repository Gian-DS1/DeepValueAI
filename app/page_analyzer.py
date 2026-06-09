"""
Individual ticker analyzer page.

Downloads OHLCV + fundamentals for a single ticker, runs the
production model (34 features), and displays:
    - Signal card (BUY / HOLD) with probability and confidence
    - Price chart with SMA 200
    - Technical indicator subplots (RSI, Williams %R, MACD)
    - Fundamental metrics summary
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data_cache import cached_download_ohlcv, cached_feature_row
from plotly.subplots import make_subplots
from theme import (
    COLORS,
    apply_plotly_theme,
    metric_card,
    metric_row,
    section_title,
)

from core.config import FEATURE_COLUMNS, PATHS
from core.prediction_service import generate_signal, load_model, load_threshold

# ---------------------------------------------------------------------------
# Cached model loading — loaded once, reused across reruns
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading production model...")
def _load_production_model():
    model = load_model(PATHS["model_file"])
    threshold = load_threshold(PATHS["threshold_file"])
    return model, threshold


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render():
    st.markdown(
        '<div class="dv-brand">'
        '<div>'
        '<div class="dv-title">Individual Analyzer</div>'
        '<div class="dv-tag">Model prediction, technicals, and fundamentals for one ticker</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # --- Input ---
    col_input, col_period, col_btn = st.columns([2, 1, 1])
    with col_input:
        ticker = st.text_input(
            "Ticker", value="AAPL", max_chars=10,
        ).upper().strip()
    with col_period:
        months_back = st.selectbox(
            "Show last",
            [3, 6, 12, 24, 60],
            index=2,
            format_func=lambda m: f"{m} months",
        )
    with col_btn:
        st.markdown('<div style="height:1.75rem;"></div>', unsafe_allow_html=True)
        analyze = st.button("Analyze", type="primary", use_container_width=True)

    if analyze:
        if not ticker:
            st.warning("Please enter a valid ticker.")
            return
        _run_analysis(ticker, months_back)


# ---------------------------------------------------------------------------
# Core analysis flow
# ---------------------------------------------------------------------------

def _run_analysis(ticker: str, months_back: int):
    # Load model
    try:
        model, threshold = _load_production_model()
    except FileNotFoundError:
        st.error(
            "Model not found. Run **`make pipeline`** to train the model."
        )
        return

    # Download OHLCV (cached 15 min — re-analyzing the same ticker is instant)
    with st.spinner(f"Downloading data for {ticker}..."):
        data = cached_download_ohlcv((ticker, "^GSPC"))

    if ticker not in data:
        st.error(f"Could not download data for **{ticker}**.")
        return

    market_df = data.get("^GSPC")

    # Feature engineering (cached — skips the slow yfinance .info call on repeats)
    with st.spinner("Computing features..."):
        df = cached_feature_row(ticker, data[ticker], market_df=market_df)

    if df.empty:
        st.error("Insufficient data to compute technical indicators.")
        return

    # Prediction on latest row
    latest = df.iloc[[-1]]
    X = latest[FEATURE_COLUMNS].values
    prob = float(model.predict_proba(X)[0, 1])
    signal_info = generate_signal(prob, threshold)

    # --- Display ---
    _show_signal_card(signal_info, threshold, df, ticker)

    # Filter to display window
    cutoff = df.index.max() - pd.DateOffset(months=months_back)
    df_display = df.loc[df.index >= cutoff]

    _plot_price_chart(df_display, ticker)
    _plot_technicals(df_display)
    _show_fundamentals(df)


# ---------------------------------------------------------------------------
# Signal card
# ---------------------------------------------------------------------------

_SIGNAL_STYLE = {
    "BUY": (COLORS["positive"], "Model signals an opportunity"),
    "HOLD": (COLORS["text_muted"], "No actionable signal"),
}


def _show_signal_card(signal_info: dict, threshold: float, df: pd.DataFrame, ticker: str):
    signal = signal_info["signal"]
    prob = signal_info["probability"]
    confidence = signal_info["confidence"]
    color, blurb = _SIGNAL_STYLE.get(signal, (COLORS["text_muted"], ""))

    latest_close = df["Close"].iloc[-1]
    latest_sma = df["sma_200"].iloc[-1] if "sma_200" in df.columns else np.nan

    # Hero banner — gradient wash keyed to the signal color.
    st.markdown(
        f"""
        <div style="
            position: relative;
            background:
                linear-gradient(135deg, {color}22 0%, transparent 60%),
                {COLORS["surface"]};
            border: 1px solid {COLORS["border"]};
            border-left: 5px solid {color};
            padding: 18px 22px;
            border-radius: 16px;
            margin-bottom: 14px;
            display: flex; align-items: center; justify-content: space-between;
            flex-wrap: wrap; gap: 12px;
        ">
            <div>
                <div style="font-size:0.75rem;letter-spacing:0.08em;text-transform:uppercase;
                            color:{COLORS["text_muted"]};font-weight:600;">{ticker}</div>
                <div style="font-size:2rem;font-weight:700;color:{color};line-height:1.1;
                            margin-top:2px;">{signal}</div>
                <div style="color:{COLORS["text_faint"]};font-size:0.85rem;
                            margin-top:2px;">{blurb}</div>
            </div>
            <div class="dv-pill" style="border-color:{color}55;color:{color};
                        background:{color}14;">
                <span style="width:7px;height:7px;border-radius:50%;background:{color};
                             display:inline-block;"></span>
                {confidence} confidence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cards = [
        metric_card("Probability", f"{prob:.1%}", accent=color),
        metric_card("Confidence", confidence),
        metric_card("Threshold", f"{threshold:.1%}"),
        metric_card("Close", f"${latest_close:,.2f}"),
        metric_card(
            "SMA 200",
            f"${latest_sma:,.2f}" if pd.notna(latest_sma) else "N/A",
        ),
    ]
    metric_row(cards, min_width=140)


# ---------------------------------------------------------------------------
# Price chart
# ---------------------------------------------------------------------------

def _plot_price_chart(df: pd.DataFrame, ticker: str):
    section_title("Price & SMA 200")

    has_ohlc = all(c in df.columns for c in ("Open", "High", "Low"))
    fig = go.Figure()

    if has_ohlc:
        # Candlesticks — the standard representation for OHLC trading data.
        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            name=ticker,
            increasing=dict(line=dict(color=COLORS["bull"]), fillcolor=COLORS["bull"]),
            decreasing=dict(line=dict(color=COLORS["bear"]), fillcolor=COLORS["bear"]),
        ))
    else:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["Close"],
            name="Price", line=dict(color=COLORS["primary"], width=2),
        ))

    if "sma_200" in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df["sma_200"],
            name="SMA 200",
            line=dict(color=COLORS["warning"], width=1.6, dash="dash"),
        ))

    apply_plotly_theme(
        fig,
        xaxis_title=None,
        yaxis_title="Price ($)",
        height=440,
        xaxis_rangeslider_visible=False,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Technical indicators
# ---------------------------------------------------------------------------

def _plot_technicals(df: pd.DataFrame):
    section_title("Technical Indicators")

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True,
        subplot_titles=("RSI (14)", "Williams %R (14)", "MACD Histogram"),
        vertical_spacing=0.09,
    )

    # RSI
    fig.add_trace(
        go.Scatter(x=df.index, y=df["rsi"], name="RSI",
                   line=dict(color=COLORS["primary"], width=1.6)),
        row=1, col=1,
    )
    fig.add_hline(y=70, line_dash="dash", line_color=COLORS["negative"], line_width=1, row=1, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color=COLORS["positive"], line_width=1, row=1, col=1)

    # Williams %R
    fig.add_trace(
        go.Scatter(x=df.index, y=df["williams_r"], name="Williams %R",
                   line=dict(color=COLORS["purple"], width=1.6)),
        row=2, col=1,
    )
    fig.add_hline(y=-80, line_dash="dash", line_color=COLORS["positive"],
                  line_width=1, row=2, col=1)
    fig.add_hline(y=-20, line_dash="dash", line_color=COLORS["negative"],
                  line_width=1, row=2, col=1)

    # MACD Histogram
    macd_vals = df["macd_histogram"]
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in macd_vals]
    fig.add_trace(
        go.Bar(x=df.index, y=macd_vals, name="MACD Hist", marker_color=colors),
        row=3, col=1,
    )

    apply_plotly_theme(
        fig,
        height=650,
        showlegend=False,
        margin=dict(t=40, b=30, l=10, r=10),
    )
    # Color the subplot titles to match the muted label style.
    for ann in fig.layout.annotations:
        ann.font.color = COLORS["text_muted"]
        ann.font.size = 12
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------

_FUND_LABELS = {
    "pe_ratio": ("PE Ratio", "num"),
    "peg_ratio": ("PEG Ratio", "num"),
    "op_margin": ("Operating Margin", "pct"),
    "revenue_growth": ("Revenue Growth", "pct"),
    "debt_equity": ("Debt / Equity", "num"),
    "current_ratio": ("Current Ratio", "num"),
    "cash_covers_debt": ("Cash / Debt", "num"),
    "fcf_yield": ("FCF Yield", "pct"),
}


def _show_fundamentals(df: pd.DataFrame):
    section_title("Fundamental Metrics")

    latest = df.iloc[-1]
    cards = []
    for key, (label, fmt) in _FUND_LABELS.items():
        val = latest.get(key)
        display = (
            (f"{val:.2%}" if fmt == "pct" else f"{val:.2f}")
            if pd.notna(val) else "N/A"
        )
        cards.append(metric_card(label, display))
    metric_row(cards, min_width=150)
