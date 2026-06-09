"""
Backtesting visualization page.

Runs the historical simulation via ``core.backtesting_engine.run_backtest``
and displays:
    - Key metric cards
    - Equity curve vs S&P 500 benchmark
    - Drawdown chart
    - Full 22-metric breakdown (5 tiers)
    - Monthly returns heatmap
    - Trade log table
"""

from datetime import date

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from theme import (
    COLORS,
    DIVERGENT_SCALE,
    apply_plotly_theme,
    metric_card,
    metric_row,
    section_title,
)

from core.backtesting_engine import run_backtest
from core.data_service import get_sp500_tickers

_TEST_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "JPM", "JNJ", "V", "PG"]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render():
    st.markdown(
        '<div class="dv-brand">'
        '<div>'
        '<div class="dv-title">Backtesting</div>'
        '<div class="dv-tag">DeepValue AI strategy vs a passive S&P 500 buy-and-hold</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # --- Configuration ---
    col1, col2, col3 = st.columns(3)
    with col1:
        mode = st.radio(
            "Universe",
            ["Test (10 tickers)", "Full S&P 500"],
            horizontal=True,
        )
    with col2:
        # SimFin free tier fundamentals start ~2020-05; use 2020-06 as safe default
        start_date = st.date_input("Start date", value=pd.Timestamp("2020-06-01"))
        end_date = st.date_input("End date", value=date.today())
    with col3:
        capital = st.number_input(
            "Initial capital ($)", value=100_000, step=10_000, min_value=10_000,
        )

    if st.button("Run Backtest", type="primary"):
        tickers = _TEST_TICKERS if "Test" in mode else get_sp500_tickers()

        with st.spinner("Running backtest... this may take several minutes."):
            try:
                result = run_backtest(
                    tickers=tickers,
                    start_date=str(start_date),
                    end_date=str(end_date),
                    initial_capital=float(capital),
                )
            except FileNotFoundError:
                st.error(
                    "Backtest model not found. "
                    "Run **`make pipeline`** to train."
                )
                return
            except RuntimeError as e:
                st.error(f"Backtest error: {e}")
                return

        st.session_state["backtest_result"] = result

    # --- Display ---
    if "backtest_result" in st.session_state:
        _display_results(st.session_state["backtest_result"])


# ---------------------------------------------------------------------------
# Results display
# ---------------------------------------------------------------------------

def _display_results(result):
    metrics = result.metrics

    _show_key_metrics(metrics)
    _plot_equity_curve(result)
    _plot_drawdown(result.equity_curve)
    _show_monthly_heatmap(metrics)
    _show_all_metrics(metrics)
    _show_trade_log(result.trades)


# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------

def _signed_accent(val) -> str:
    """Green for non-negative, red for negative — for return-like metrics."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return COLORS["text_muted"]
    return COLORS["positive"] if val >= 0 else COLORS["negative"]


def _show_key_metrics(m: dict):
    section_title("Summary")

    def fmt(val, spec):
        return spec.format(val) if val is not None else "N/A"

    cards = [
        metric_card("Total Return", fmt(m.get("total_return"), "{:.2%}"),
                    accent=_signed_accent(m.get("total_return"))),
        metric_card("Annualized Return", fmt(m.get("annualized_return"), "{:.2%}"),
                    accent=_signed_accent(m.get("annualized_return"))),
        metric_card("Sharpe Ratio", fmt(m.get("sharpe_ratio"), "{:.2f}")),
        metric_card("Max Drawdown", fmt(m.get("max_drawdown"), "{:.2%}"),
                    accent=COLORS["negative"]),
        metric_card("Win Rate", fmt(m.get("win_rate"), "{:.1%}")),
        metric_card("Alpha vs S&P 500", fmt(m.get("alpha"), "{:.2%}"),
                    accent=_signed_accent(m.get("alpha"))),
    ]
    metric_row(cards, min_width=150)


# ---------------------------------------------------------------------------
# Equity curve
# ---------------------------------------------------------------------------

def _plot_equity_curve(result):
    section_title("Equity Curve vs S&P 500")

    fig = go.Figure()
    # Strategy — solid line with a soft area fill for depth.
    fig.add_trace(go.Scatter(
        x=result.equity_curve.index,
        y=result.equity_curve.values,
        name="DeepValue AI",
        line=dict(color=COLORS["positive"], width=2.4),
        fill="tozeroy",
        fillcolor="rgba(34,197,94,0.08)",
    ))
    fig.add_trace(go.Scatter(
        x=result.benchmark_curve.index,
        y=result.benchmark_curve.values,
        name="S&P 500 (Buy & Hold)",
        line=dict(color=COLORS["text_muted"], width=1.8, dash="dash"),
    ))
    apply_plotly_theme(
        fig,
        xaxis_title=None,
        yaxis_title="Portfolio Value ($)",
        height=480,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Drawdown
# ---------------------------------------------------------------------------

def _plot_drawdown(equity_curve: pd.Series):
    section_title("Drawdown")

    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values,
        fill="tozeroy",
        name="Drawdown",
        line=dict(color=COLORS["negative"], width=1.2),
        fillcolor="rgba(239, 68, 68, 0.22)",
    ))
    apply_plotly_theme(
        fig,
        xaxis_title=None,
        yaxis_title="Drawdown",
        height=300,
        yaxis_tickformat=".1%",
        margin=dict(t=20, b=40, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# Monthly returns heatmap
# ---------------------------------------------------------------------------

def _show_monthly_heatmap(metrics: dict):
    monthly_raw = metrics.get("monthly_returns")
    if not monthly_raw:
        return

    section_title("Monthly Returns")

    # Build a DataFrame with year x month
    records = []
    for date_str, ret in monthly_raw.items():
        dt = pd.Timestamp(date_str)
        records.append({"year": dt.year, "month": dt.month, "return": ret})

    df = pd.DataFrame(records)
    if df.empty:
        return

    pivot = df.pivot_table(index="year", columns="month", values="return", aggfunc="first")
    pivot.columns = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ][:len(pivot.columns)]

    # Divergent scale (red → neutral → green) from the shared theme; numeric
    # labels in every cell so the chart is readable without relying on color.
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=[str(y) for y in pivot.index],
        colorscale=DIVERGENT_SCALE,
        zmid=0,
        xgap=3, ygap=3,
        text=[[f"{v:.1%}" if pd.notna(v) else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=11, color=COLORS["text"]),
        colorbar=dict(
            title="Return", tickformat=".0%",
            outlinecolor=COLORS["border"], outlinewidth=1,
            tickfont=dict(color=COLORS["text_muted"]),
        ),
        hovertemplate="%{y} %{x}: %{z:.2%}<extra></extra>",
    ))
    apply_plotly_theme(
        fig,
        height=max(220, 64 * len(pivot)),
        margin=dict(t=20, b=30, l=10, r=10),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------------------------
# All 22 metrics — 5 tiers
# ---------------------------------------------------------------------------

_METRIC_TIERS = {
    "Return": [
        ("total_return", "Total Return", "pct"),
        ("annualized_return", "Annualized Return", "pct"),
        ("roi_on_invested", "ROI on Invested Capital", "pct"),
        ("benchmark_return", "Benchmark Return", "pct"),
        ("alpha", "Alpha", "pct"),
    ],
    "Risk": [
        ("max_drawdown", "Max Drawdown", "pct"),
        ("max_drawdown_duration", "Max DD Duration (days)", "int"),
        ("volatility", "Annualized Volatility", "pct"),
        ("value_at_risk", "VaR 95%", "pct"),
        ("conditional_var", "CVaR 95%", "pct"),
    ],
    "Risk-Adjusted": [
        ("sharpe_ratio", "Sharpe Ratio", "dec"),
        ("sortino_ratio", "Sortino Ratio", "dec"),
        ("calmar_ratio", "Calmar Ratio", "dec"),
        ("omega_ratio", "Omega Ratio", "dec"),
        ("recovery_factor", "Recovery Factor", "dec"),
    ],
    "Trade Quality": [
        ("win_rate", "Win Rate", "pct"),
        ("profit_factor", "Profit Factor", "dec"),
        ("avg_win_vs_avg_loss", "Avg Win / Avg Loss", "dec"),
        ("num_trades", "Total Trades", "int"),
    ],
    "Consistency": [
        ("positive_months_pct", "Positive Months", "pct"),
        ("ulcer_index", "Ulcer Index", "dec"),
    ],
}


def _fmt_metric(val, kind: str) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if kind == "pct":
        return f"{val:.2%}"
    if kind == "int":
        return f"{val:,.0f}"
    return f"{val:.2f}"


def _show_all_metrics(metrics: dict):
    with st.expander("All metrics (22 metrics, 5 tiers)"):
        for tier_name, items in _METRIC_TIERS.items():
            st.markdown(
                f'<div style="color:{COLORS["text_muted"]};font-size:0.74rem;'
                'text-transform:uppercase;letter-spacing:0.07em;font-weight:600;'
                'margin:4px 0 2px 0;">' + tier_name + "</div>",
                unsafe_allow_html=True,
            )
            cards = [
                metric_card(label, _fmt_metric(metrics.get(key), kind))
                for key, label, kind in items
            ]
            metric_row(cards, min_width=150)


# ---------------------------------------------------------------------------
# Trade log
# ---------------------------------------------------------------------------

_TRADE_FMT = {
    "price": "${:.2f}",
    "shares": "{:.2f}",
    "value": "${:,.0f}",
    "return_pct": "{:.2%}",
}


def _show_trade_log(trades: pd.DataFrame):
    section_title("Trade Log")

    if trades.empty:
        st.info("No trades were executed during this period.")
        return

    # Summary
    n_buys = int((trades["action"] == "BUY").sum())
    n_sells = int(trades["action"].isin(["SELL", "SELL_PARTIAL"]).sum())
    st.caption(f"{n_buys} buys · {n_sells} sells · {len(trades)} total trades")

    # Display
    display_cols = [c for c in ["date", "ticker", "action", "price", "shares",
                                 "value", "reason", "return_pct"] if c in trades.columns]
    fmt = {k: v for k, v in _TRADE_FMT.items() if k in display_cols}

    st.dataframe(
        trades[display_cols].style.format(fmt, na_rep="—"),
        use_container_width=True,
        height=400,
        hide_index=True,
    )

    # Download
    csv = trades.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download trades (CSV)",
        data=csv,
        file_name="backtest_trades.csv",
        mime="text/csv",
    )
