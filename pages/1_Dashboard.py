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
from modules.state import init_session_state, render_active_group_selector, require_analysis
from modules.tradingview import render_tradingview_chart, yahoo_to_tradingview

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

render_active_group_selector(key="dashboard_active_group")

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
            ("VaR histórico", INDICATOR_HELP["var_historico"]),
            ("CVaR 95%", INDICATOR_HELP["cvar"]),
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
    "VaR 95% paramétrico (mensual)",
    "VaR 95% histórico (mensual)",
    "CVaR 95% (mensual)",
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
            "VaR 95% paramétrico (mensual)": "{:.2%}",
            "VaR 95% histórico (mensual)": "{:.2%}",
            "CVaR 95% (mensual)": "{:.2%}",
        },
    ),
    use_container_width=True,
)

st.subheader("Riesgo — VaR y CVaR por portafolio")
st.caption(
    "Valores en % = pérdida estimada sobre el capital del portafolio en un mes. "
    "Paramétrico asume normalidad; histórico usa la cola empírica; "
    "CVaR = severidad media de esa cola. "
    "Con capital configurado también se muestra la pérdida en dinero."
)
capital = float(st.session_state.get("capital") or 0.0)
risk_tabs = st.tabs(list(portfolios.keys()))
for tab, (name, portfolio) in zip(risk_tabs, portfolios.items()):
    with tab:
        m1, m2, m3 = st.columns(3)
        with m1:
            show_metric(
                "VaR 95% paramétrico",
                format_percent(portfolio.get("var_parametric_95")),
                help_key="var",
            )
        with m2:
            show_metric(
                "VaR 95% histórico",
                format_percent(portfolio.get("var_historical_95")),
                help_key="var_historico",
            )
        with m3:
            show_metric(
                "CVaR 95%",
                format_percent(portfolio.get("cvar_95")),
                help_key="cvar",
            )
        if capital > 0:
            n1, n2, n3 = st.columns(3)
            with n1:
                show_metric(
                    "VaR paramétrico ($)",
                    format_compact(portfolio.get("var_parametric_95_money")),
                    help_key="var",
                )
            with n2:
                show_metric(
                    "VaR histórico ($)",
                    format_compact(portfolio.get("var_historical_95_money")),
                    help_key="var_historico",
                )
            with n3:
                show_metric(
                    "CVaR ($)",
                    format_compact(portfolio.get("cvar_95_money")),
                    help_key="cvar",
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
        "VaR 95% paramétrico (mensual)",
        "VaR 95% histórico (mensual)",
        "CVaR 95% (mensual)",
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
            "VaR 95% paramétrico (mensual)": "{:.2%}",
            "VaR 95% histórico (mensual)": "{:.2%}",
            "CVaR 95% (mensual)": "{:.2%}",
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

st.subheader("TradingView — activo seleccionado")
st.caption(
    "Gráfico interactivo en tiempo real (widget oficial TradingView). "
    "Elige un ticker del análisis actual. Índices Yahoo (ej. ^GSPC) "
    "se mapean automáticamente al símbolo TradingView equivalente."
)
ticker_options = list(prices.columns)
default_idx = 0
tv_col1, tv_col2 = st.columns([2, 1])
with tv_col1:
    selected_tv = st.selectbox(
        "Activo",
        ticker_options,
        index=default_idx,
        key="dashboard_tradingview_ticker",
    )
with tv_col2:
    show_metric(
        "Símbolo TradingView",
        yahoo_to_tradingview(selected_tv),
        help_text="Símbolo enviado al widget tras mapear desde Yahoo Finance.",
    )

try:
    used_symbol = render_tradingview_chart(
        selected_tv,
        watchlist=ticker_options,
    )
    st.caption(f"Mostrando **{selected_tv}** → TradingView `{used_symbol}`.")
except Exception as exc:  # noqa: BLE001
    st.warning(f"No se pudo cargar TradingView para {selected_tv}: {exc}")

st.subheader("Pesos — Máximo Sharpe")
st.caption(INDICATOR_HELP["peso"])
st.plotly_chart(
    weights_bar_chart(
        portfolios["Máximo Sharpe"]["weights"],
        title="Distribución de pesos (Máximo Sharpe)",
    ),
    use_container_width=True,
)
