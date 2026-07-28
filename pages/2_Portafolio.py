"""Página Portafolio — selección de activos y generación de los 3 portafolios."""

from __future__ import annotations

import streamlit as st

from modules.charts import correlation_heatmap, covariance_heatmap
from modules.helpers import (
    INDICATOR_HELP,
    apply_theme,
    format_percent,
    show_metric,
    theme_styler,
)
from modules.portfolio import portfolios_summary_table
from modules.state import init_session_state, parse_tickers_input, run_full_analysis

st.set_page_config(page_title="Portafolio", layout="wide")
apply_theme()
init_session_state()

st.title("Portafolio")
st.caption(
    "Descarga precios diarios, calcula en mensual/anual y genera siempre "
    "3 portafolios: Equiponderado, Máximo Sharpe y Mínima varianza."
)

raw = st.text_input(
    "Tickers (separados por coma)",
    value=st.session_state.tickers_input,
    help="Ejemplo: MSFT, GOOGL, AMZN, V, COST, CVX, LMT",
)
st.session_state.tickers_input = raw

c1, c2, c3 = st.columns(3)
with c1:
    show_metric("Periodo histórico", st.session_state.period, help_key="periodo")
with c2:
    show_metric("Benchmark (mercado)", st.session_state.benchmark, help_key="benchmark")
with c3:
    show_metric(
        "Rf (tasa libre de riesgo)",
        format_percent(st.session_state.risk_free_rate),
        help_key="rf",
    )
analyze = st.button("Analizar portafolios", type="primary")

if analyze:
    tickers = parse_tickers_input(raw)
    if not tickers:
        st.error("Escribe al menos un ticker válido.")
    else:
        with st.spinner("Descargando datos y construyendo portafolios..."):
            try:
                run_full_analysis(tickers)
                st.success(
                    f"Análisis completado para: {', '.join(st.session_state.tickers)}"
                )
            except Exception as exc:  # noqa: BLE001
                st.session_state.analysis_ready = False
                st.session_state.last_error = str(exc)
                st.error(f"Error en el análisis: {exc}")

if st.session_state.get("analysis_ready") and st.session_state.get("portfolios"):
    st.subheader("Resumen de los 3 portafolios")
    st.caption(
        "Rendimiento = retorno esperado · Desviacion E. = riesgo (σ) · "
        "Sharpe / Treynor / Jensen / Beta = ratios de desempeño."
    )
    table = portfolios_summary_table(st.session_state.portfolios)
    st.dataframe(
        theme_styler(
            table,
            {
                "Rendimiento (mensual)": "{:.2%}",
                "Rendimiento (anual)": "{:.2%}",
                "Varianza (mensual)": "{:.6f}",
                "Varianza (anual)": "{:.6f}",
                "Desviacion E. (mensual)": "{:.2%}",
                "Desviacion E. (anual)": "{:.2%}",
                "Beta": "{:.4f}",
                "Sharpe (anual)": "{:.4f}",
                "Treynor": "{:.4f}",
                "Jensen": "{:.4f}",
            },
        ),
        use_container_width=True,
    )

    st.subheader("Pesos por portafolio")
    tabs = st.tabs(list(st.session_state.portfolios.keys()))
    for tab, (name, portfolio) in zip(tabs, st.session_state.portfolios.items()):
        with tab:
            weights = portfolio["weights"]
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            with m1:
                show_metric(
                    "Retorno mensual",
                    format_percent(portfolio["rendimiento_mensual"]),
                    help_key="retorno_mensual",
                )
            with m2:
                show_metric(
                    "Retorno anual",
                    format_percent(portfolio["rendimiento_anual"]),
                    help_key="retorno_anual",
                )
            with m3:
                show_metric(
                    "Riesgo mensual (σ)",
                    format_percent(portfolio["desviacion_estandar_mensual"]),
                    help_key="riesgo_mensual",
                )
            with m4:
                show_metric(
                    "Riesgo anual (σ)",
                    format_percent(portfolio["desviacion_estandar_anual"]),
                    help_key="riesgo_anual",
                )
            with m5:
                show_metric(
                    "Sharpe",
                    f"{portfolio['sharpe']:.4f}",
                    help_key="sharpe",
                )
            with m6:
                show_metric(
                    "Beta",
                    f"{portfolio['beta']:.4f}",
                    help_key="beta",
                )
            st.caption(INDICATOR_HELP["peso"])
            st.dataframe(
                theme_styler(
                    weights.rename("Peso (% del capital)").map(lambda x: f"{x:.2%}").to_frame()
                ),
                use_container_width=True,
            )
            if portfolio.get("asset_betas") is not None:
                st.caption(
                    "Beta individual de cada activo vs el benchmark "
                    "(usadas en SUMAPRODUCTO para el Beta del portafolio)."
                )
                st.dataframe(
                    theme_styler(
                        portfolio["asset_betas"]
                        .rename("Beta (vs benchmark)")
                        .map(lambda x: f"{x:.4f}")
                        .to_frame()
                    ),
                    use_container_width=True,
                )

    st.subheader("Matriz de covarianzas (mensual)")
    cov = st.session_state.get("covariance")
    if cov is None or getattr(cov, "empty", True):
        st.warning("Sin matriz de covarianzas. Vuelve a pulsar Analizar.")
    else:
        st.caption(INDICATOR_HELP["covarianza"])
        st.dataframe(theme_styler(cov, "{:.6f}"), use_container_width=True)
        st.plotly_chart(
            covariance_heatmap(cov, title="Heatmap de covarianzas (mensual)"),
            use_container_width=True,
        )

    st.subheader("Matriz de correlaciones (mensual) + heatmap")
    corr = st.session_state.get("correlation")
    if corr is None or getattr(corr, "empty", True):
        st.warning("Sin matriz de correlaciones. Vuelve a pulsar Analizar.")
    else:
        st.caption(INDICATOR_HELP["correlacion"])
        st.dataframe(theme_styler(corr, "{:.2%}"), use_container_width=True)
        st.plotly_chart(
            correlation_heatmap(corr, title="Heatmap de correlaciones (mensual)"),
            use_container_width=True,
        )
else:
    st.info("Pulsa **Analizar portafolios** para generar resultados.")
