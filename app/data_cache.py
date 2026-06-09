"""Streamlit caching layer for the dashboard's expensive operations.

The bottleneck across every page is network I/O to Yahoo Finance, not the
model (which predicts in milliseconds). Profiling a single-ticker analysis:
    download OHLCV ~2.9s | fundamentals .info ~0.4s | features ~0.2s | model ~0s

Without caching, every click on Analyze / Scan / Run Backtest re-downloads
everything from scratch — even re-running the same ticker seconds later.

This module wraps the core data functions in ``st.cache_data`` with a 15-minute
TTL. Daily market data doesn't change intraday in a way that matters for these
signals, so a 15-minute window makes repeated analysis effectively instant
while still refreshing several times per hour.

WHY A SEPARATE MODULE:
    ``core/`` must stay UI-agnostic (no Streamlit imports), so the cache
    decorators live here in the app layer and delegate to core functions.
    Cached functions must return picklable, hashable-arg values — we pass
    tuples of tickers (not lists) and return plain dicts/DataFrames.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.backtesting_engine import BacktestResult, run_backtest
from core.data_service import (
    build_feature_row,
    download_ohlcv,
    download_ohlcv_batch,
)
from core.screener_engine import scan_sp500

# 15 minutes. Tune in one place.
_TTL = 900


# ---------------------------------------------------------------------------
# OHLCV downloads
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def cached_download_ohlcv(
    tickers: tuple[str, ...],
    period: str = "7y",
) -> dict[str, pd.DataFrame]:
    """Cached OHLCV download for a small set of tickers (Analyzer/Backtest).

    Args are a tuple so Streamlit can hash them. Uses the batch path, which
    falls back to per-ticker internally for single symbols.
    """
    return download_ohlcv_batch(list(tickers), period=period)


@st.cache_data(ttl=_TTL, show_spinner=False)
def cached_single_ohlcv(ticker: str, period: str = "7y") -> dict[str, pd.DataFrame]:
    """Cached download for one ticker plus its market/VIX references.

    Kept separate from the tuple-based helper so the Analyzer's most common
    action (one ticker) gets a clean, stable cache key.
    """
    return download_ohlcv([ticker], period=period)


# ---------------------------------------------------------------------------
# Feature engineering (Analyzer)
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def cached_feature_row(
    ticker: str,
    ohlcv_df: pd.DataFrame,
    market_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Cached feature engineering for one ticker.

    Streamlit hashes the DataFrame args, so identical inputs (same ticker,
    same OHLCV frame within the TTL) skip recomputation and the slow
    ``yf.Ticker().info`` fundamentals call inside build_feature_row.
    """
    return build_feature_row(ticker, ohlcv_df, market_df=market_df)


# ---------------------------------------------------------------------------
# Screener
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def cached_scan(
    tickers: tuple[str, ...] | None,
    include_failing: bool,
) -> pd.DataFrame:
    """Cached S&P 500 scan. Re-running the same scan within the TTL is instant.

    ``tickers`` is a tuple (or None for the full S&P 500) so the args hash.
    """
    ticker_list = list(tickers) if tickers is not None else None
    return scan_sp500(tickers=ticker_list, include_failing=include_failing)


# ---------------------------------------------------------------------------
# Backtesting
# ---------------------------------------------------------------------------
@st.cache_data(ttl=_TTL, show_spinner=False)
def cached_backtest(
    tickers: tuple[str, ...],
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> BacktestResult:
    """Cached backtest. Re-running the identical configuration is instant.

    The result is a picklable dataclass (dict + DataFrames + Series), so it
    caches cleanly. ``tickers`` is a tuple so the args hash.
    """
    return run_backtest(
        tickers=list(tickers),
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )


def clear_caches() -> None:
    """Clear all cached data (used by a manual 'Refresh data' control)."""
    cached_download_ohlcv.clear()
    cached_single_ohlcv.clear()
    cached_feature_row.clear()
    cached_scan.clear()
    cached_backtest.clear()
