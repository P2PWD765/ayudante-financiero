"""
Estado compartido de la aplicación Streamlit (session_state).

Centraliza inicialización y el pipeline de análisis para que
las páginas solo rendericen resultados.

Soporta varios grupos de tickers, cada uno con su propio benchmark.
El grupo activo se refleja en las claves planas (prices, portfolios, …)
para que Dashboard / Optimización / Riesgo sigan igual.
"""

from __future__ import annotations

import importlib
import uuid
from typing import Any

import pandas as pd
import streamlit as st

import config
from modules.classification import classify_tickers
from modules.data import (
    align_with_benchmark,
    download_benchmark,
    download_prices,
    get_fundamentals,
)
from modules import metrics
from modules import optimization
from modules import portfolio


_ANALYSIS_FLAT_KEYS = (
    "tickers",
    "tickers_input",
    "benchmark",
    "prices",
    "benchmark_prices",
    "fundamentals",
    "yahoo_refs",
    "metrics_summary",
    "portfolios",
    "markowitz",
    "monthly_returns",
    "covariance",
    "covariance_annual",
    "correlation",
    "classification",
    "active_group_name",
)


def _reload_business_modules() -> None:
    """Fuerza recarga de módulos para evitar caché vieja de Streamlit."""
    importlib.reload(metrics)
    importlib.reload(optimization)
    importlib.reload(portfolio)


def _new_group_id() -> str:
    return f"g_{uuid.uuid4().hex[:8]}"


def default_analysis_groups() -> list[dict[str, Any]]:
    """Plantilla inicial: un grupo con tickers y benchmark por defecto."""
    return [
        {
            "id": _new_group_id(),
            "name": "Grupo 1",
            "tickers_input": "AAPL, MSFT, GOOGL",
            "benchmark": config.DEFAULT_BENCHMARK,
            "enabled": True,
        }
    ]


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
        "classification": None,
        "analysis_ready": False,
        "last_error": None,
        "montecarlo_result": None,
        "montecarlo_portfolio": None,
        "black_litterman": None,
        "bl_views_df": None,
        "analysis_groups": None,
        "group_results": {},
        "active_group_id": None,
        "active_group_name": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    if not st.session_state.analysis_groups:
        st.session_state.analysis_groups = default_analysis_groups()
        st.session_state.active_group_id = st.session_state.analysis_groups[0]["id"]


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


def _analyze_one_group(
    tickers: list[str],
    *,
    period: str,
    benchmark: str,
    risk_free_rate: float,
    capital: float,
) -> dict[str, Any]:
    """Ejecuta el pipeline para un solo grupo y devuelve el payload."""
    prices = download_prices(tickers, period=period)
    bench = download_benchmark(benchmark, period=period)
    prices, bench = align_with_benchmark(prices, bench)

    fundamentals = get_fundamentals(list(prices.columns))
    yahoo_refs = get_yahoo_reference_metrics(list(prices.columns))
    metrics_summary = metrics.summary_metrics(
        prices,
        benchmark_prices=bench,
        risk_free_rate=risk_free_rate,
    )

    if "Beta" in metrics_summary.columns and "Beta (Yahoo)" in yahoo_refs.columns:
        metrics_summary = metrics_summary.join(yahoo_refs[["Beta (Yahoo)"]], how="left")

    portfolios = portfolio.build_standard_portfolios(
        prices,
        benchmark_prices=bench,
        risk_free_rate=risk_free_rate,
        capital=capital,
    )

    monthly_rets, _mu_m, cov_m, corr_m = portfolio.estimate_monthly_inputs(prices)
    mu_a, cov_a = portfolio.estimate_annual_inputs(prices)
    markowitz = optimization.run_markowitz_analysis(
        mu_a, cov_a, risk_free_rate=risk_free_rate
    )
    classification = classify_tickers(list(prices.columns), benchmark)

    return {
        "tickers": list(prices.columns),
        "tickers_input": ", ".join(prices.columns),
        "benchmark": benchmark,
        "prices": prices,
        "benchmark_prices": bench,
        "fundamentals": fundamentals,
        "yahoo_refs": yahoo_refs,
        "metrics_summary": metrics_summary,
        "portfolios": portfolios,
        "markowitz": markowitz,
        "monthly_returns": monthly_rets,
        "covariance": cov_m,
        "covariance_annual": cov_a,
        "correlation": corr_m,
        "classification": classification,
    }


def apply_group_to_session(group_id: str | None = None) -> bool:
    """Copia el resultado del grupo activo a las claves planas de session_state.

    Args:
        group_id: Grupo a activar (default: active_group_id).

    Returns:
        True si había resultados para ese grupo.
    """
    gid = group_id or st.session_state.get("active_group_id")
    results = st.session_state.get("group_results") or {}
    if not gid or gid not in results:
        return False

    payload = results[gid]
    st.session_state.active_group_id = gid
    for key in _ANALYSIS_FLAT_KEYS:
        if key in payload:
            st.session_state[key] = payload[key]

    # Localizar nombre del grupo
    name = payload.get("active_group_name")
    if not name:
        for group in st.session_state.get("analysis_groups") or []:
            if group.get("id") == gid:
                name = group.get("name", gid)
                break
    st.session_state.active_group_name = name or gid
    st.session_state.analysis_ready = True
    return True


def set_active_group(group_id: str) -> None:
    """Cambia el grupo activo y limpia resultados dependientes (MC / BL)."""
    if apply_group_to_session(group_id):
        st.session_state.montecarlo_result = None
        st.session_state.montecarlo_portfolio = None
        st.session_state.black_litterman = None
        st.session_state.bl_views_df = None


def run_full_analysis(
    tickers: list[str],
    period: str | None = None,
    benchmark: str | None = None,
    risk_free_rate: float | None = None,
    capital: float | None = None,
) -> None:
    """Analiza un único set de tickers (compatibilidad) como grupo activo."""
    groups = st.session_state.get("analysis_groups") or default_analysis_groups()
    active_id = st.session_state.get("active_group_id") or groups[0]["id"]

    for group in groups:
        if group["id"] == active_id:
            group["tickers_input"] = ", ".join(tickers)
            if benchmark:
                group["benchmark"] = benchmark
            group["enabled"] = True
            break
    else:
        groups[0]["tickers_input"] = ", ".join(tickers)
        if benchmark:
            groups[0]["benchmark"] = benchmark
        active_id = groups[0]["id"]

    st.session_state.analysis_groups = groups
    st.session_state.active_group_id = active_id
    run_groups_analysis(
        period=period,
        risk_free_rate=risk_free_rate,
        capital=capital,
        only_group_ids=[active_id],
    )


def run_groups_analysis(
    *,
    period: str | None = None,
    risk_free_rate: float | None = None,
    capital: float | None = None,
    only_group_ids: list[str] | None = None,
) -> list[str]:
    """Analiza los grupos habilitados (o un subconjunto) y sincroniza el activo.

    Args:
        period: Periodo histórico.
        risk_free_rate: Rf anual.
        capital: Capital.
        only_group_ids: Si se pasa, solo analiza esos ids.

    Returns:
        Lista de ids analizados con éxito.

    Raises:
        ValueError: Si no hay grupos válidos para analizar.
    """
    period = period or st.session_state.period
    rf = (
        st.session_state.risk_free_rate
        if risk_free_rate is None
        else risk_free_rate
    )
    capital = st.session_state.capital if capital is None else capital

    st.session_state.last_error = None
    _reload_business_modules()

    groups = st.session_state.get("analysis_groups") or []
    to_run: list[dict[str, Any]] = []
    for group in groups:
        if only_group_ids is not None and group["id"] not in only_group_ids:
            continue
        if not group.get("enabled", True):
            continue
        tickers = parse_tickers_input(group.get("tickers_input", ""))
        if not tickers:
            continue
        to_run.append({**group, "_tickers": tickers})

    if not to_run:
        st.session_state.analysis_ready = False
        raise ValueError(
            "No hay grupos habilitados con tickers. "
            "Añade al menos una fila con símbolos válidos."
        )

    results: dict[str, Any] = dict(st.session_state.get("group_results") or {})
    # Si analizamos todos los habilitados, reemplazamos resultados viejos de ids no presentes.
    if only_group_ids is None:
        keep_ids = {g["id"] for g in to_run}
        results = {k: v for k, v in results.items() if k in keep_ids}

    analyzed: list[str] = []
    errors: list[str] = []

    for group in to_run:
        gid = group["id"]
        bench = (group.get("benchmark") or config.DEFAULT_BENCHMARK).strip().upper()
        try:
            payload = _analyze_one_group(
                group["_tickers"],
                period=period,
                benchmark=bench,
                risk_free_rate=rf,
                capital=capital,
            )
            payload["active_group_name"] = group.get("name", gid)
            payload["group_id"] = gid
            results[gid] = payload
            analyzed.append(gid)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{group.get('name', gid)}: {exc}")

    st.session_state.group_results = results
    st.session_state.period = period
    st.session_state.risk_free_rate = rf
    st.session_state.capital = capital
    st.session_state.montecarlo_result = None
    st.session_state.montecarlo_portfolio = None
    st.session_state.black_litterman = None
    st.session_state.bl_views_df = None

    if not analyzed:
        st.session_state.analysis_ready = False
        st.session_state.last_error = "; ".join(errors) if errors else "Sin resultados."
        raise ValueError(st.session_state.last_error)

    # Activar el primer grupo analizado (o conservar activo si sigue válido).
    active = st.session_state.get("active_group_id")
    if active not in results:
        active = analyzed[0]
    apply_group_to_session(active)

    if errors:
        st.session_state.last_error = "; ".join(errors)

    return analyzed


def add_analysis_group(
    *,
    name: str | None = None,
    tickers_input: str = "",
    benchmark: str | None = None,
) -> dict[str, Any] | None:
    """Añade una fila/grupo si no se superó el máximo.

    Returns:
        El grupo creado, o None si ya hay MAX_ANALYSIS_GROUPS.
    """
    groups = list(st.session_state.get("analysis_groups") or [])
    if len(groups) >= config.MAX_ANALYSIS_GROUPS:
        return None

    group = {
        "id": _new_group_id(),
        "name": name or f"Grupo {len(groups) + 1}",
        "tickers_input": tickers_input,
        "benchmark": (benchmark or st.session_state.get("benchmark")
                      or config.DEFAULT_BENCHMARK),
        "enabled": True,
    }
    groups.append(group)
    st.session_state.analysis_groups = groups
    return group


def remove_analysis_group(group_id: str) -> None:
    """Elimina un grupo (deja al menos uno)."""
    groups = [g for g in (st.session_state.get("analysis_groups") or []) if g["id"] != group_id]
    if not groups:
        groups = default_analysis_groups()
    st.session_state.analysis_groups = groups

    results = dict(st.session_state.get("group_results") or {})
    results.pop(group_id, None)
    st.session_state.group_results = results

    if st.session_state.get("active_group_id") == group_id:
        st.session_state.active_group_id = groups[0]["id"]
        if groups[0]["id"] in results:
            apply_group_to_session(groups[0]["id"])
        else:
            st.session_state.analysis_ready = False


def render_active_group_selector(*, key: str = "active_group_selector") -> None:
    """Selector de grupo activo para Dashboard / Optimización / Riesgo."""
    groups = st.session_state.get("analysis_groups") or []
    results = st.session_state.get("group_results") or {}
    ready = [g for g in groups if g["id"] in results]
    if len(ready) <= 1:
        if ready:
            st.caption(
                f"Grupo activo: **{ready[0].get('name', ready[0]['id'])}** · "
                f"Benchmark `{ready[0].get('benchmark')}`"
            )
        return

    labels = {
        g["id"]: f"{g.get('name', g['id'])} ({g.get('benchmark', '')})"
        for g in ready
    }
    ids = list(labels.keys())
    current = st.session_state.get("active_group_id")
    index = ids.index(current) if current in ids else 0
    chosen = st.selectbox(
        "Grupo de análisis activo",
        options=ids,
        index=index,
        format_func=lambda i: labels[i],
        key=key,
        help="Cada grupo tiene sus tickers y su propio benchmark.",
    )
    if chosen != st.session_state.get("active_group_id"):
        set_active_group(chosen)
        st.rerun()


def require_analysis() -> bool:
    """Indica si ya hay un análisis listo; si no, muestra aviso."""
    if st.session_state.get("analysis_ready") and st.session_state.get("portfolios"):
        return True
    st.warning(
        "Todavía no hay un análisis. Ve a **Portafolio**, define grupos/tickers "
        "y pulsa **Analizar portafolios**."
    )
    return False
