"""
Estado compartido de la aplicación Streamlit (session_state).

Centraliza inicialización y el pipeline de análisis para que
las páginas solo rendericen resultados.
"""

from __future__ import annotations

import importlib
from typing import Any

import pandas as pd
import streamlit as st

import config
from modules.data import (
    align_with_benchmark,
    download_benchmark,
    download_prices,
    get_fundamentals,
)
from modules import metrics
from modules import optimization
from modules import portfolio


def _reload_business_modules() -> None:
    """Fuerza recarga de módulos para evitar caché vieja de Streamlit."""
    importlib.reload(metrics)
    importlib.reload(optimization)
    importlib.reload(portfolio)


def init_session_state() -> None:
    """Inicializa claves por defecto en st.session_state."""
    defaults: dict[str, Any] = {
        "tickers_input": "AAPL, MSFT, GOOGL",
        "tickers": ["AAPL", "MSFT", "GOOGL"],
        "period": config.DEFAULT_PERIOD,
        "benchmark": config.DEFAULT_BENCHMARK,
        "risk_free_rate": config.RISK_FREE_RATE,
        "capital": 100_000.0,
        "prices": None,
        "benchmark_prices": None,
        "fundamentals": None,
        "yahoo_refs": None,
        "metrics_summary": None,
        "portfolios": None,
        "markowitz": None,
        "covariance": None,
        "covariance_annual": None,
        "correlation": None,
        "monthly_returns": None,
        "analysis_ready": False,
        "last_error": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def parse_tickers_input(raw: str) -> list[str]:
    """Convierte texto 'AAPL, MSFT' en lista de tickers."""
    parts = [p.strip().upper() for p in raw.replace(";", ",").split(",")]
    return [p for p in parts if p]


def get_yahoo_reference_metrics(tickers: list[str]) -> pd.DataFrame:
    """Obtiene métricas de referencia publicadas por Yahoo (ej. Beta).

    Args:
        tickers: Lista de símbolos.

    Returns:
        DataFrame indexado por ticker.
    """
    import yfinance as yf
    from modules.helpers import safe_get

    rows = []
    for symbol in tickers:
        row: dict[str, Any] = {"Ticker": symbol}
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:  # noqa: BLE001
            info = {}
        for field_key, field_label in config.YAHOO_REFERENCE_FIELDS.items():
            value = safe_get(info, field_key, default=pd.NA)
            row[field_label] = pd.to_numeric(value, errors="coerce")
        rows.append(row)
    return pd.DataFrame(rows).set_index("Ticker")


def run_full_analysis(
    tickers: list[str],
    period: str | None = None,
    benchmark: str | None = None,
    risk_free_rate: float | None = None,
    capital: float | None = None,
) -> None:
    """Ejecuta el pipeline completo y guarda resultados en session_state.

    Args:
        tickers: Activos seleccionados por el usuario.
        period: Periodo histórico (ej. 5y).
        benchmark: Símbolo del benchmark.
        risk_free_rate: Rf anual.
        capital: Capital del portafolio.
    """
    period = period or st.session_state.period
    benchmark = benchmark or st.session_state.benchmark
    rf = (
        st.session_state.risk_free_rate
        if risk_free_rate is None
        else risk_free_rate
    )
    capital = st.session_state.capital if capital is None else capital

    st.session_state.last_error = None
    st.session_state.analysis_ready = False

    # Evita que Streamlit use una versión vieja de portfolio.py en memoria.
    _reload_business_modules()

    prices = download_prices(tickers, period=period)
    bench = download_benchmark(benchmark, period=period)
    prices, bench = align_with_benchmark(prices, bench)

    fundamentals = get_fundamentals(list(prices.columns))
    yahoo_refs = get_yahoo_reference_metrics(list(prices.columns))
    metrics_summary = metrics.summary_metrics(
        prices,
        benchmark_prices=bench,
        risk_free_rate=rf,
    )

    # Comparación dual Beta: Calculado vs Yahoo
    if "Beta" in metrics_summary.columns and "Beta (Yahoo)" in yahoo_refs.columns:
        metrics_summary = metrics_summary.join(yahoo_refs[["Beta (Yahoo)"]], how="left")

    portfolios = portfolio.build_standard_portfolios(
        prices,
        benchmark_prices=bench,
        risk_free_rate=rf,
        capital=capital,
    )

    monthly_rets, mu_m, cov_m, corr_m = portfolio.estimate_monthly_inputs(prices)
    mu_a, cov_a = portfolio.estimate_annual_inputs(prices)
    markowitz = optimization.run_markowitz_analysis(mu_a, cov_a, risk_free_rate=rf)

    st.session_state.tickers = list(prices.columns)
    st.session_state.prices = prices
    st.session_state.benchmark_prices = bench
    st.session_state.fundamentals = fundamentals
    st.session_state.yahoo_refs = yahoo_refs
    st.session_state.metrics_summary = metrics_summary
    st.session_state.portfolios = portfolios
    st.session_state.markowitz = markowitz
    st.session_state.monthly_returns = monthly_rets
    st.session_state.covariance = cov_m  # mensual (como Excel)
    st.session_state.covariance_annual = cov_a
    st.session_state.correlation = corr_m
    st.session_state.period = period
    st.session_state.benchmark = benchmark
    st.session_state.risk_free_rate = rf
    st.session_state.capital = capital
    st.session_state.analysis_ready = True


def require_analysis() -> bool:
    """Indica si ya hay un análisis listo; si no, muestra aviso."""
    if st.session_state.get("analysis_ready") and st.session_state.get("portfolios"):
        return True
    st.warning(
        "Todavía no hay un análisis. Ve a **Portafolio**, ingresa tickers "
        "y pulsa **Analizar portafolios**."
    )
    return False
