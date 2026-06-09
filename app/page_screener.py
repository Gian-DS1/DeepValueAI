"""
S&P 500 screener page.

Scans the S&P 500 (or a small test list) using the production model
and displays a ranked table of investment opportunities with filters.
"""

import pandas as pd
import streamlit as st
from data_cache import cached_scan, clear_caches
from theme import COLORS, metric_card, metric_row, section_title

_TEST_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "JNJ", "V", "PG"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render():
    st.markdown(
        '<div class="dv-brand">'
        '<div>'
        '<div class="dv-title">S&P 500 Screener</div>'
        '<div class="dv-tag">Rank the index by model conviction (34 features)</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # --- Controls ---
    col1, col2 = st.columns([2, 1])
    with col1:
        mode = st.radio(
            "Scan mode",
            ["Quick test (10 tickers)", "Full S&P 500 (~15 min)"],
            horizontal=True,
        )
    with col2:
        show_all = st.checkbox("Include tickers without signal", value=True)

    col_scan, col_refresh = st.columns([4, 1])
    with col_scan:
        do_scan = st.button("Scan", type="primary", use_container_width=True)
    with col_refresh:
        if st.button("Refresh data", use_container_width=True,
                     help="Clear the 15-min cache and re-download"):
            clear_caches()
            st.session_state.pop("screener_results", None)
            st.rerun()

    if do_scan:
        # tuple (hashable) for the cache key; None = full S&P 500
        tickers = tuple(_TEST_TICKERS) if "Quick" in mode else None

        with st.spinner("Scanning... this may take a few minutes (cached 15 min)."):
            try:
                results = cached_scan(tickers, show_all)
            except FileNotFoundError:
                st.error(
                    "Model not found. Run **`make pipeline`** to train."
                )
                return

        if results.empty:
            st.warning("No results found.")
            return

        st.session_state["screener_results"] = results

    # --- Results ---
    if "screener_results" in st.session_state:
        _display_results(st.session_state["screener_results"])


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

_DISPLAY_COLS = [
    "ticker", "close", "probability", "signal_strength",
    "signal_freshness_days", "sma_headroom_pct", "passes_filters",
    "pe_ratio", "peg_ratio", "fcf_yield",
]

# Mapping from internal column names to user-friendly display names.
_COLUMN_LABELS = {
    "ticker": "Ticker",
    "close": "Price",
    "probability": "Buy Prob.",
    "signal_strength": "Strength",
    "signal_freshness_days": "Signal Days",
    "sma_headroom_pct": "SMA Margin",
    "passes_filters": "Passes",
    "pe_ratio": "P/E",
    "peg_ratio": "PEG",
    "fcf_yield": "FCF Yield",
}

_FORMAT_MAP = {
    "probability": "{:.1%}",
    "signal_strength": "{:.1%}",
    "sma_headroom_pct": "{:.1%}",
    "close": "${:.2f}",
    "pe_ratio": "{:.1f}",
    "peg_ratio": "{:.2f}",
    "fcf_yield": "{:.2%}",
}


def _display_results(df: pd.DataFrame):
    # KPI summary cards
    n_pass = int(df["passes_filters"].sum())
    n_total = len(df)
    avg_prob = df["probability"].mean() if "probability" in df.columns else float("nan")
    top_prob = df["probability"].max() if "probability" in df.columns else float("nan")

    metric_row(
        [
            metric_card("Opportunities", f"{n_pass}", sub=f"of {n_total} analyzed",
                        accent=COLORS["positive"]),
            metric_card("Tickers Analyzed", f"{n_total:,}"),
            metric_card("Avg Buy Prob.", f"{avg_prob:.1%}" if pd.notna(avg_prob) else "N/A"),
            metric_card("Top Buy Prob.", f"{top_prob:.1%}" if pd.notna(top_prob) else "N/A",
                        accent=COLORS["primary"]),
        ],
        min_width=160,
    )

    section_title("Ranked Results")

    # Filter controls
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_prob = st.slider("Minimum probability", 0.0, 1.0, 0.0, 0.05)
    with col_f2:
        only_passing = st.checkbox("Only tickers passing filters", value=False)

    filtered = df[df["probability"] >= min_prob].copy()
    if only_passing:
        filtered = filtered[filtered["passes_filters"]].copy()

    if filtered.empty:
        st.info("No tickers match the selected filters.")
        return

    # Select available columns
    available = [c for c in _DISPLAY_COLS if c in filtered.columns]

    # Format columns for display (avoid pandas Styler — it has
    # compatibility issues with Streamlit's dark theme that make
    # text invisible). Instead, format values directly in the DataFrame.
    display_df = filtered[available].copy()
    for col, fmt_str in _FORMAT_MAP.items():
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(
                lambda v, f=fmt_str: f.format(v) if pd.notna(v) else "N/A"
            )

    # Rename columns to user-friendly labels
    rename = {c: _COLUMN_LABELS.get(c, c) for c in display_df.columns}
    display_df = display_df.rename(columns=rename)

    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
        hide_index=True,
        column_config={
            "Buy Prob.": st.column_config.TextColumn(
                "Buy Prob.", help="Model probability the stock rises"),
            "Passes": st.column_config.TextColumn(
                "Passes", help="Meets quality + signal filters"),
        },
    )

    # Download button
    csv = filtered[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv,
        file_name="screener_results.csv",
        mime="text/csv",
    )
