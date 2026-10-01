"""Página Riesgo — VaR/CVaR de portafolios y simulación Monte Carlo."""

from __future__ import annotations

import streamlit as st

import config
from modules.charts import (
    montecarlo_fan_chart,
    montecarlo_final_histogram,
    montecarlo_scenarios_chart,
)
from modules.helpers import (
    INDICATOR_HELP,
    apply_theme,
    format_compact,
    format_percent,
    show_metric,
    theme_styler,
)
from modules.montecarlo import SCENARIO_ORDER, simulate_scenarios_from_portfolio
from modules.state import init_session_state, render_active_group_selector, require_analysis

st.set_page_config(page_title="Riesgo", layout="wide")
apply_theme()
init_session_state()

st.title("Riesgo")
st.caption(
    "VaR / CVaR del análisis actual y simulación Monte Carlo "
    "con tres escenarios: Pesimista, Normal y Optimista."
)

if not require_analysis():
    st.stop()

render_active_group_selector(key="riesgo_active_group")

portfolios = st.session_state.portfolios
monthly = st.session_state.monthly_returns
capital = float(st.session_state.get("capital") or 100_000.0)

# ---------------------------------------------------------------------------
# VaR / CVaR
# ---------------------------------------------------------------------------
st.subheader("VaR y CVaR (mensual, 95%)")
st.caption(
    f"{INDICATOR_HELP['var']} · {INDICATOR_HELP['var_historico']} · "
    f"{INDICATOR_HELP['cvar']}"
)

var_tabs = st.tabs(list(portfolios.keys()))
for tab, (name, portfolio) in zip(var_tabs, portfolios.items()):
    with tab:
        m1, m2, m3 = st.columns(3)
        with m1:
            show_metric(
                "VaR paramétrico",
                format_percent(portfolio.get("var_parametric_95")),
                help_key="var",
            )
        with m2:
            show_metric(
                "VaR histórico",
                format_percent(portfolio.get("var_historical_95")),
                help_key="var_historico",
            )
        with m3:
            show_metric(
                "CVaR",
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

# ---------------------------------------------------------------------------
# Monte Carlo — 3 escenarios
# ---------------------------------------------------------------------------
st.subheader("Simulación Monte Carlo — 3 escenarios")
st.caption(
    "Misma muestra aleatoria en los tres casos. "
    "**Normal:** μ y σ históricos. "
    "**Pesimista:** μ − 1·σ por activo y volatilidad ×1.25. "
    "**Optimista:** μ + 1·σ por activo y volatilidad ×0.85. "
    "Acumulación: V_t = V_{t-1} · exp(r_p)."
)

portfolio_names = list(portfolios.keys())
c1, c2, c3, c4 = st.columns(4)
with c1:
    selected_name = st.selectbox("Portafolio", portfolio_names, index=0)
with c2:
    n_sims = st.number_input(
        "Simulaciones",
        min_value=500,
        max_value=20_000,
        value=int(config.MONTE_CARLO_SIMULATIONS),
        step=500,
    )
with c3:
    horizon = st.number_input(
        "Horizonte (meses)",
        min_value=1,
        max_value=120,
        value=int(config.MONTE_CARLO_HORIZON_MONTHS),
        step=1,
    )
with c4:
    seed = st.number_input(
        "Semilla RNG",
        min_value=0,
        max_value=999_999,
        value=int(config.MONTE_CARLO_SEED),
        step=1,
    )

run_mc = st.button("Ejecutar Monte Carlo", type="primary")

if run_mc:
    if monthly is None or getattr(monthly, "empty", True):
        st.error("No hay retornos mensuales en el análisis. Vuelve a Analizar en Portafolio.")
    else:
        with st.spinner("Simulando escenarios Pesimista / Normal / Optimista..."):
            try:
                bundle = simulate_scenarios_from_portfolio(
                    portfolios[selected_name],
                    monthly,
                    n_simulations=int(n_sims),
                    horizon_months=int(horizon),
                    initial_value=capital,
                    seed=int(seed),
                )
                st.session_state.montecarlo_result = bundle
                st.session_state.montecarlo_portfolio = selected_name
                st.success(
                    f"Monte Carlo listo (3 escenarios): {selected_name} · "
                    f"{int(n_sims):,} sims · {int(horizon)} meses."
                )
            except Exception as exc:  # noqa: BLE001
                st.session_state.montecarlo_result = None
                st.error(f"Error en Monte Carlo: {exc}")

bundle = st.session_state.get("montecarlo_result")
if not bundle or "scenarios" not in bundle:
    st.info("Elige un portafolio y pulsa **Ejecutar Monte Carlo**.")
    st.stop()

scenarios = bundle["scenarios"]
params = bundle.get("scenario_params", {})

st.caption(
    f"Portafolio: **{st.session_state.get('montecarlo_portfolio', '—')}** "
    f"| Capital inicial: {format_compact(bundle['initial_value'])}"
)

st.markdown("##### Comparación de escenarios")
st.dataframe(
    theme_styler(
        bundle["comparison"],
        {
            "Valor medio final": "{:,.2f}",
            "Mediana final": "{:,.2f}",
            "P5 final": "{:,.2f}",
            "P95 final": "{:,.2f}",
            "Retorno medio": "{:.2%}",
            "Prob. pérdida": "{:.2%}",
            "VaR 95% (MC)": "{:.2%}",
            "CVaR 95% (MC)": "{:.2%}",
            "VaR 95% ($)": "{:,.2f}",
            "CVaR 95% ($)": "{:,.2f}",
        },
    ),
    use_container_width=True,
)

st.plotly_chart(
    montecarlo_scenarios_chart(
        scenarios,
        title=(
            "Medianas por escenario — "
            f"{st.session_state.get('montecarlo_portfolio', '')}"
        ),
    ),
    use_container_width=True,
)

detail_tabs = st.tabs(list(SCENARIO_ORDER))
for tab, scen_name in zip(detail_tabs, SCENARIO_ORDER):
    with tab:
        result = scenarios[scen_name]
        summary = result["summary"]
        p = params.get(scen_name, {})
        st.caption(
            f"Ajuste: μ {p.get('mu_shift_sigma', 0):+.1f}·σ · "
            f"volatilidad ×{p.get('vol_scale', 1):.2f}"
        )

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            show_metric("Valor medio final", format_compact(summary["mean_final"]))
        with k2:
            show_metric("Mediana final", format_compact(summary["median_final"]))
        with k3:
            show_metric("P5 final", format_compact(summary["p5_final"]))
        with k4:
            show_metric("P95 final", format_compact(summary["p95_final"]))

        k5, k6, k7, k8 = st.columns(4)
        with k5:
            show_metric("Retorno medio", format_percent(summary["mean_return"]))
        with k6:
            show_metric("Prob. de pérdida", format_percent(summary["prob_loss"]))
        with k7:
            show_metric(
                "VaR 95% (MC)",
                format_percent(summary["var_95"]),
                help_text=(
                    "VaR Monte Carlo 95% al horizonte "
                    f"({summary['horizon_months']} meses). Positivo = pérdida."
                ),
            )
        with k8:
            show_metric(
                "CVaR 95% (MC)",
                format_percent(summary["cvar_95"]),
                help_text="Media de pérdidas en el peor 5% de simulaciones.",
            )

        m1, m2 = st.columns(2)
        with m1:
            show_metric("VaR 95% MC ($)", format_compact(summary["var_95_money"]))
        with m2:
            show_metric("CVaR 95% MC ($)", format_compact(summary["cvar_95_money"]))

        st.plotly_chart(
            montecarlo_fan_chart(
                result["percentiles"],
                result["paths"],
                title=f"Trayectorias — {scen_name}",
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            montecarlo_final_histogram(
                result["final_values"],
                initial_value=summary["initial_value"],
                title=f"Distribución final — {scen_name}",
            ),
            use_container_width=True,
        )

        with st.expander(f"Percentiles por mes — {scen_name}"):
            st.dataframe(result["percentiles"], use_container_width=True)
