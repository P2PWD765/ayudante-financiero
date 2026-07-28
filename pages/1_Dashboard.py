"""Página Dashboard — resumen, métricas, fundamentales y gráficos."""

from __future__ import annotations

import streamlit as st

from modules.charts import (
    correlation_heatmap,
    covariance_heatmap,
    cumulative_returns_chart,
    price_evolution_chart,
    risk_return_scatter,
    weights_bar_chart,
)
from modules.helpers import (
    INDICATOR_HELP,
    apply_theme,
    format_compact,
    format_percent,
    show_metric,
    theme_styler,
)
from modules import metrics
from modules.portfolio import portfolios_summary_table
from modules.state import init_session_state, require_analysis

st.set_page_config(page_title="Dashboard", layout="wide")
apply_theme()
init_session_state()

st.title("Dashboard")
st.caption(
    "Precios diarios descargados de Yahoo; métricas calculadas en "
    "**mensual** y **anual** (sin vistas diarias)."
)

if not require_analysis():
    st.stop()

prices = st.session_state.prices
portfolios = st.session_state.portfolios
summary = st.session_state.metrics_summary
fundamentals = st.session_state.fundamentals
corr = st.session_state.correlation
cov = st.session_state.covariance
markowitz = st.session_state.markowitz

st.subheader("Resumen rápido")
c1, c2, c3, c4 = st.columns(4)
with c1:
    show_metric("Activos (tickers)", len(st.session_state.tickers), help_key="activos")
with c2:
    show_metric("Periodo histórico", st.session_state.period, help_key="periodo")
with c3:
    show_metric("Benchmark (mercado)", st.session_state.benchmark, help_key="benchmark")
with c4:
    show_metric(
        "Rf (tasa libre de riesgo)",
        format_percent(st.session_state.risk_free_rate),
        help_key="rf",
    )

with st.expander("¿Qué significa cada indicador?"):
    st.markdown(
        "\n".join(f"- **{k}:** {v}" for k, v in [
            ("Rf", INDICATOR_HELP["rf"]),
            ("Riesgo (σ)", INDICATOR_HELP["riesgo_anual"]),
            ("Retorno", INDICATOR_HELP["retorno_anual"]),
            ("Sharpe", INDICATOR_HELP["sharpe"]),
            ("Beta", INDICATOR_HELP["beta"]),
            ("Treynor", INDICATOR_HELP["treynor"]),
            ("Jensen (Alpha)", INDICATOR_HELP["jensen"]),
            ("VaR 95%", INDICATOR_HELP["var"]),
            ("Peso", INDICATOR_HELP["peso"]),
            ("Correlación", INDICATOR_HELP["correlacion"]),
            ("Covarianza", INDICATOR_HELP["covarianza"]),
        ])
    )

st.subheader("Los 3 portafolios (mensual y anual)")
st.caption(
    "Cada columna indica la métrica: **Rendimiento** = retorno esperado · "
    "**Desviacion E.** = riesgo (σ) · **Sharpe / Treynor / Jensen / Beta** = ratios."
)
port_cols = [
    "Rendimiento (mensual)",
    "Rendimiento (anual)",
    "Varianza (mensual)",
    "Varianza (anual)",
    "Desviacion E. (mensual)",
    "Desviacion E. (anual)",
    "Beta",
    "Sharpe (anual)",
    "Treynor",
    "Jensen",
]
port_table = portfolios_summary_table(portfolios)
port_table = port_table[[c for c in port_cols if c in port_table.columns]]
st.dataframe(
    theme_styler(
        port_table,
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

st.subheader("Métricas por activo (mensual y anual)")
st.caption(
    "Valores en **%** = rendimientos o riesgo · **Beta / Sharpe / Alpha** = ratios "
    "(sin %). Hover en el glosario de arriba si dudas. "
    "Beta calculado vs Beta Yahoo cuando exista."
)
metric_cols = [
    c
    for c in [
        "Rendimiento acumulado",
        "Rendimiento (mensual)",
        "Rendimiento (anual)",
        "Varianza (mensual)",
        "Varianza (anual)",
        "Desviacion E. (mensual)",
        "Desviacion E. (anual)",
        "Sharpe (anual)",
        "VaR 95% (mensual)",
        "Beta",
        "Beta (Yahoo)",
        "Alpha de Jensen",
    ]
    if c in summary.columns
]
st.dataframe(
    theme_styler(
        summary[metric_cols],
        {
            "Rendimiento acumulado": "{:.2%}",
            "Rendimiento (mensual)": "{:.2%}",
            "Rendimiento (anual)": "{:.2%}",
            "Varianza (mensual)": "{:.6f}",
            "Varianza (anual)": "{:.6f}",
            "Desviacion E. (mensual)": "{:.2%}",
            "Desviacion E. (anual)": "{:.2%}",
            "Sharpe (anual)": "{:.4f}",
            "VaR 95% (mensual)": "{:.4f}",
            "Beta": "{:.4f}",
            "Beta (Yahoo)": "{:.4f}",
            "Alpha de Jensen": "{:.4f}",
        },
    ),
    use_container_width=True,
)

st.subheader("Fundamentales (Yahoo Finance)")
st.caption(
    "Market Cap / Enterprise Value = tamaño · EV/EBITDA y P/S = múltiplos de valoración · "
    "ROA / ROE = rentabilidad contable (en %)."
)
fund_display = fundamentals.copy()
for col in ["Market Cap", "Enterprise Value"]:
    if col in fund_display.columns:
        fund_display[col] = fund_display[col].map(format_compact)
for col in ["ROA", "ROE"]:
    if col in fund_display.columns:
        fund_display[col] = fund_display[col].map(
            lambda x: format_percent(x) if x == x else "N/A"
        )
st.dataframe(theme_styler(fund_display), use_container_width=True)

st.subheader("Matriz de covarianzas (mensual)")
st.caption(INDICATOR_HELP["covarianza"] + " Calculada con retornos log mensuales (n-1).")
if cov is None or cov.empty:
    st.warning("No hay matriz de covarianzas disponible. Vuelve a analizar en Portafolio.")
else:
    st.dataframe(
        theme_styler(cov, "{:.6f}"),
        use_container_width=True,
    )
    st.plotly_chart(
        covariance_heatmap(cov, title="Heatmap de covarianzas (mensual)"),
        use_container_width=True,
    )

st.subheader("Matriz de correlaciones + heatmap")
st.caption(INDICATOR_HELP["correlacion"])
if corr is None or corr.empty:
    st.warning("No hay matriz de correlaciones disponible. Vuelve a analizar en Portafolio.")
else:
    st.dataframe(
        theme_styler(corr, "{:.2%}"),
        use_container_width=True,
    )
    st.plotly_chart(
        correlation_heatmap(corr, title="Mapa de calor de correlaciones (mensual)"),
        use_container_width=True,
    )

st.subheader("Gráficos de precios / desempeño")
st.caption(
    "Eje Y en precios = nivel de precio (base 100) · "
    "Rendimiento acumulado = ganancia/pérdida acumulada en % · "
    "Riesgo vs retorno = volatilidad anual (eje X) frente a retorno anual (eje Y)."
)
g1, g2 = st.columns(2)
with g1:
    st.plotly_chart(
        price_evolution_chart(
            prices,
            title="Evolución de precios (base 100)",
            normalize=True,
        ),
        use_container_width=True,
    )
with g2:
    st.plotly_chart(
        cumulative_returns_chart(
            metrics.cumulative_returns(prices),
            title="Rendimiento acumulado",
        ),
        use_container_width=True,
    )

port_points = {
    name: {
        "volatility": p["desviacion_estandar_anual"],
        "expected_return": p["rendimiento_anual"],
    }
    for name, p in portfolios.items()
}
st.plotly_chart(
    risk_return_scatter(
        markowitz["assets"],
        port_points,
        title="Riesgo vs rendimiento (anual)",
    ),
    use_container_width=True,
)

st.subheader("Pesos — Máximo Sharpe")
st.caption(INDICATOR_HELP["peso"])
st.plotly_chart(
    weights_bar_chart(
        portfolios["Máximo Sharpe"]["weights"],
        title="Distribución de pesos (Máximo Sharpe)",
    ),
    use_container_width=True,
)
