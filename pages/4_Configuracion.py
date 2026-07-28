"""Página Configuración — parámetros generales y exportación."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

import config
from modules.export import export_analysis_to_csv_folder, export_analysis_to_excel
from modules.helpers import apply_theme, format_percent, show_metric
from modules.state import init_session_state

st.set_page_config(page_title="Configuración", layout="wide")
apply_theme()
init_session_state()

st.title("Configuración")
st.caption("Parámetros generales del análisis y exportación de resultados.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Parámetros")
    period = st.selectbox(
        "Periodo histórico",
        options=["1y", "2y", "5y", "10y", "max"],
        index=["1y", "2y", "5y", "10y", "max"].index(st.session_state.period)
        if st.session_state.period in ["1y", "2y", "5y", "10y", "max"]
        else 2,
        help="Ventana de precios a descargar de Yahoo Finance.",
    )
    benchmark = st.text_input(
        "Benchmark / mercado de referencia (Yahoo)",
        value=st.session_state.benchmark,
        help="Ejemplo: ^GSPC = S&P 500. Se usa para Beta y Alpha.",
    )
    risk_free_rate = st.number_input(
        "Tasa libre de riesgo anual — Rf (decimal)",
        min_value=0.0,
        max_value=1.0,
        value=float(st.session_state.risk_free_rate),
        step=0.005,
        format="%.4f",
        help="Ejemplo: 0.04 = 4% anual. Se usa en Sharpe, Treynor y Jensen.",
    )
    capital = st.number_input(
        "Capital del portafolio (moneda)",
        min_value=0.0,
        value=float(st.session_state.capital),
        step=1000.0,
        format="%.2f",
        help="Monto total invertido. Se usa en VaR y valuación de pesos.",
    )

with col2:
    st.subheader("Estado actual")
    show_metric("Periodo histórico", st.session_state.period, help_key="periodo")
    show_metric("Benchmark (mercado)", st.session_state.benchmark, help_key="benchmark")
    show_metric(
        "Rf (tasa libre de riesgo)",
        format_percent(st.session_state.risk_free_rate),
        help_key="rf",
    )
    show_metric(
        "Capital del portafolio",
        f"{st.session_state.capital:,.2f}",
        help_key="capital",
    )
    st.caption(
        f"Comparación Yahoo: "
        f"{'Activada' if config.SHOW_YAHOO_COMPARISON else 'Desactivada'} · "
        "Fuente de datos: Yahoo Finance (yfinance)."
    )
if st.button("Guardar configuración", type="primary"):
    st.session_state.period = period
    st.session_state.benchmark = benchmark.strip().upper() or config.DEFAULT_BENCHMARK
    st.session_state.risk_free_rate = float(risk_free_rate)
    st.session_state.capital = float(capital)
    st.success("Configuración guardada. Vuelve a analizar en **Portafolio** para aplicar cambios.")

st.divider()
st.subheader("Exportación")

if not st.session_state.get("analysis_ready"):
    st.info("Primero genera un análisis en la página Portafolio.")
else:
    export_name = st.text_input("Nombre base del archivo", value="analisis_portafolio")
    c1, c2 = st.columns(2)

    with c1:
        if st.button("Exportar a Excel"):
            path = Path("exports") / f"{export_name}.xlsx"
            try:
                export_analysis_to_excel(
                    path,
                    prices=st.session_state.prices,
                    fundamentals=st.session_state.fundamentals,
                    metrics_summary=st.session_state.metrics_summary,
                    portfolios=st.session_state.portfolios,
                    covariance=st.session_state.covariance,
                    correlation=st.session_state.correlation,
                    frontier=st.session_state.markowitz["frontier"],
                    cal=st.session_state.markowitz["cal"],
                )
                st.success(f"Excel guardado en: `{path}`")
                with open(path, "rb") as f:
                    st.download_button(
                        "Descargar Excel",
                        data=f,
                        file_name=path.name,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo exportar Excel: {exc}")

    with c2:
        if st.button("Exportar a CSV (carpeta)"):
            folder = Path("exports") / f"{export_name}_csv"
            try:
                paths = export_analysis_to_csv_folder(
                    folder,
                    prices=st.session_state.prices,
                    fundamentals=st.session_state.fundamentals,
                    metrics_summary=st.session_state.metrics_summary,
                    portfolios=st.session_state.portfolios,
                    covariance=st.session_state.covariance,
                    correlation=st.session_state.correlation,
                    frontier=st.session_state.markowitz["frontier"],
                    cal=st.session_state.markowitz["cal"],
                )
                st.success(f"Se generaron {len(paths)} CSV en `{folder}`")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo exportar CSV: {exc}")
