"""Página Optimización — frontera eficiente y Capital Allocation Line."""

from __future__ import annotations

import streamlit as st

from modules.charts import (
    capital_allocation_line_chart,
    efficient_frontier_chart,
    weights_bar_chart,
)
from modules.helpers import apply_theme, format_percent, show_metric, theme_styler
from modules.state import init_session_state, require_analysis

st.set_page_config(page_title="Optimización", layout="wide")
apply_theme()
init_session_state()

st.title("Optimización")
st.caption("Frontera eficiente de Markowitz y Capital Allocation Line (CAL).")

if not require_analysis():
    st.stop()

markowitz = st.session_state.markowitz
portfolios = st.session_state.portfolios

min_var = markowitz["min_variance"]
max_sharpe = markowitz["max_sharpe"]

st.subheader("Portafolios clave")
st.caption(
    "Aquí **riesgo** = volatilidad anual (σ) y **retorno** = rendimiento esperado anual. "
    "No son variaciones respecto a otro mes; son métricas del portafolio."
)
r1 = st.columns(3)
with r1[0]:
    show_metric(
        "Rf (tasa libre de riesgo)",
        format_percent(markowitz["risk_free_rate"]),
        help_key="rf",
    )
with r1[1]:
    show_metric(
        "Mín. varianza — Riesgo anual (σ)",
        format_percent(min_var["volatility"]),
        help_key="riesgo_anual",
    )
with r1[2]:
    show_metric(
        "Mín. varianza — Retorno esperado",
        format_percent(min_var["expected_return"]),
        help_key="retorno_anual",
    )

r2 = st.columns(2)
with r2[0]:
    show_metric(
        "Máx. Sharpe — Riesgo anual (σ)",
        format_percent(max_sharpe["volatility"]),
        help_key="riesgo_anual",
    )
with r2[1]:
    show_metric(
        "Máx. Sharpe — Retorno esperado",
        format_percent(max_sharpe["expected_return"]),
        help_key="retorno_anual",
    )

m1, m2 = st.columns(2)
with m1:
    st.write("**Pesos — Mínima varianza**")
    st.caption("Peso = % del capital en cada ticker (suma 100%).")
    st.dataframe(
        theme_styler(
            min_var["weights"].rename("Peso (% del capital)").map(lambda x: f"{x:.2%}").to_frame()
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        weights_bar_chart(min_var["weights"], title="Mínima varianza — pesos (% del capital)"),
        use_container_width=True,
    )
with m2:
    st.write("**Pesos — Máximo Sharpe (tangencial)**")
    st.caption("Peso = % del capital en cada ticker (suma 100%).")
    st.dataframe(
        theme_styler(
            max_sharpe["weights"]
            .rename("Peso (% del capital)")
            .map(lambda x: f"{x:.2%}")
            .to_frame()
        ),
        use_container_width=True,
    )
    st.plotly_chart(
        weights_bar_chart(max_sharpe["weights"], title="Máximo Sharpe — pesos (% del capital)"),
        use_container_width=True,
    )

st.subheader("Frontera eficiente + CAL")
st.caption(
    "Eje X = **riesgo anual (σ)** · Eje Y = **retorno esperado anual**. "
    "La frontera une portafolios óptimos; la CAL une Rf con el Máx. Sharpe."
)
st.plotly_chart(
    efficient_frontier_chart(
        frontier=markowitz["frontier"],
        cal=markowitz["cal"],
        assets=markowitz["assets"],
        min_variance=min_var,
        max_sharpe=max_sharpe,
        risk_free_rate=markowitz["risk_free_rate"],
    ),
    use_container_width=True,
)

st.subheader("Capital Allocation Line (CAL)")
st.caption(
    "Línea de asignación: combina activo libre de riesgo (Rf) y el portafolio tangencial "
    "(Máx. Sharpe). Eje X = riesgo · Eje Y = retorno esperado."
)
st.plotly_chart(
    capital_allocation_line_chart(
        cal=markowitz["cal"],
        max_sharpe=max_sharpe,
        risk_free_rate=markowitz["risk_free_rate"],
    ),
    use_container_width=True,
)

with st.expander("Datos de la frontera eficiente"):
    st.caption(
        "volatility = riesgo anual (σ) · expected_return = retorno esperado anual · "
        "sharpe = ratio de Sharpe."
    )
    st.dataframe(
        theme_styler(
            markowitz["frontier"][["volatility", "expected_return", "sharpe"]].rename(
                columns={
                    "volatility": "Riesgo anual (σ)",
                    "expected_return": "Retorno esperado anual",
                    "sharpe": "Sharpe",
                }
            ),
            {
                "Riesgo anual (σ)": "{:.2%}",
                "Retorno esperado anual": "{:.2%}",
                "Sharpe": "{:.4f}",
            },
        ),
        use_container_width=True,
    )

with st.expander("Datos de la CAL"):
    st.caption(
        "risky_weight = % invertido en el portafolio riesgoso · "
        "volatility = riesgo · expected_return = retorno esperado."
    )
    st.dataframe(
        theme_styler(
            markowitz["cal"].rename(
                columns={
                    "risky_weight": "% en portafolio riesgoso",
                    "volatility": "Riesgo anual (σ)",
                    "expected_return": "Retorno esperado anual",
                }
            ),
            {
                "% en portafolio riesgoso": "{:.2%}",
                "Riesgo anual (σ)": "{:.2%}",
                "Retorno esperado anual": "{:.2%}",
            },
        ),
        use_container_width=True,
    )

st.info(
    "Comparación con los 3 portafolios del módulo Portafolio: "
    f"Equiponderado Sharpe={portfolios['Equiponderado']['sharpe']:.4f}, "
    f"Máx. Sharpe={portfolios['Máximo Sharpe']['sharpe']:.4f}, "
    f"Mín. Varianza={portfolios['Mínima varianza']['sharpe']:.4f}."
)
