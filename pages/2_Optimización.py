"""Página Optimización — Markowitz (frontera/CAL) y Black-Litterman."""

from __future__ import annotations

import pandas as pd
import streamlit as st

import config
from modules.black_litterman import default_views_template, run_black_litterman
from modules.charts import (
    capital_allocation_line_chart,
    efficient_frontier_chart,
    weights_bar_chart,
)
from modules.helpers import apply_theme, format_percent, show_metric, theme_styler
from modules.state import init_session_state, render_active_group_selector, require_analysis

st.set_page_config(page_title="Optimización", layout="wide")
apply_theme()
init_session_state()

st.title("Optimización")
st.caption(
    "Markowitz (frontera eficiente + CAL) y Black-Litterman "
    "(views del usuario + prior de equilibrio)."
)

if not require_analysis():
    st.stop()

render_active_group_selector(key="optim_active_group")

markowitz = st.session_state.markowitz
portfolios = st.session_state.portfolios
tab_mk, tab_bl = st.tabs(["Markowitz", "Black-Litterman"])

# ---------------------------------------------------------------------------
# Markowitz
# ---------------------------------------------------------------------------
with tab_mk:
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
                min_var["weights"]
                .rename("Peso (% del capital)")
                .map(lambda x: f"{x:.2%}")
                .to_frame()
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            weights_bar_chart(
                min_var["weights"],
                title="Mínima varianza — pesos (% del capital)",
            ),
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
            weights_bar_chart(
                max_sharpe["weights"],
                title="Máximo Sharpe — pesos (% del capital)",
            ),
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

# ---------------------------------------------------------------------------
# Black-Litterman
# ---------------------------------------------------------------------------
with tab_bl:
    st.subheader("Black-Litterman")
    st.caption(
        "Prior de equilibrio **π = δ Σ w_mercado** (w por Market Cap si existe; "
        "si no, equiponderado). Luego se incorporan **views** absolutas o relativas "
        "para obtener retornos posteriores y un Máx. Sharpe Black-Litterman."
    )

    tickers = list(st.session_state.tickers)
    mu = markowitz["assets"]["expected_return"]
    cov = st.session_state.covariance_annual
    if cov is None or getattr(cov, "empty", True):
        st.error("No hay covarianza anual. Vuelve a analizar en Portafolio.")
        st.stop()

    p1, p2, p3 = st.columns(3)
    with p1:
        tau = st.number_input(
            "Tau (τ) — incertidumbre del prior",
            min_value=0.001,
            max_value=1.0,
            value=float(config.BL_TAU),
            step=0.01,
            format="%.3f",
            help="Valores típicos: 0.025–0.05. Más alto = confías menos en el equilibrio.",
        )
    with p2:
        delta = st.number_input(
            "Delta (δ) — aversión al riesgo",
            min_value=0.1,
            max_value=10.0,
            value=float(config.BL_DELTA),
            step=0.1,
            format="%.2f",
            help="Escala el prior: π = δ Σ w. Típico ~2–3.",
        )
    with p3:
        show_metric(
            "Rf",
            format_percent(st.session_state.risk_free_rate),
            help_key="rf",
        )

    st.markdown("##### Views del usuario")
    st.caption(
        "**absoluta:** retorno esperado anual del activo (ej. MSFT = 12%). "
        "**relativa:** diferencial anual asset − other (ej. MSFT bate a GOOGL en +2%). "
        "**confianza:** 0.05–1 (más alto = la view pesa más)."
    )

    if st.session_state.get("bl_views_df") is None:
        st.session_state.bl_views_df = pd.DataFrame(default_views_template(tickers))
    else:
        current_assets = set(
            st.session_state.bl_views_df.get("asset", pd.Series(dtype=str))
            .astype(str)
            .str.upper()
        )
        if not current_assets.intersection(set(tickers)):
            st.session_state.bl_views_df = pd.DataFrame(default_views_template(tickers))

    edited = st.data_editor(
        st.session_state.bl_views_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "type": st.column_config.SelectboxColumn(
                "Tipo",
                options=["absoluta", "relativa"],
                required=True,
            ),
            "asset": st.column_config.SelectboxColumn(
                "Activo",
                options=tickers,
                required=True,
            ),
            "other": st.column_config.SelectboxColumn(
                "Otro (solo relativa)",
                options=tickers,
                required=False,
            ),
            "return": st.column_config.NumberColumn(
                "Retorno / diferencial anual",
                help="Absoluta: retorno esperado. Relativa: asset − other.",
                step=0.01,
                format="%.4f",
                required=True,
            ),
            "confidence": st.column_config.NumberColumn(
                "Confianza (0–1)",
                min_value=0.05,
                max_value=1.0,
                step=0.05,
                format="%.2f",
                required=True,
            ),
        },
        key="bl_views_editor",
    )
    st.session_state.bl_views_df = edited

    run_bl = st.button("Calcular Black-Litterman", type="primary")

    if run_bl:
        views_raw = edited.fillna("").to_dict(orient="records")
        views: list[dict] = []
        for row in views_raw:
            asset = str(row.get("asset", "")).strip().upper()
            if not asset:
                continue
            views.append(
                {
                    "type": str(row.get("type", "absoluta")).strip().lower(),
                    "asset": asset,
                    "other": str(row.get("other", "")).strip().upper(),
                    "return": float(row.get("return", 0.0)),
                    "confidence": float(
                        row.get("confidence", config.BL_DEFAULT_CONFIDENCE)
                    ),
                }
            )
        if not views:
            st.error("Añade al menos una view con activo válido.")
        else:
            try:
                result = run_black_litterman(
                    mu,
                    cov,
                    views,
                    fundamentals=st.session_state.get("fundamentals"),
                    risk_free_rate=st.session_state.risk_free_rate,
                    tau=float(tau),
                    delta=float(delta),
                )
                st.session_state.black_litterman = result
                st.success("Black-Litterman calculado.")
            except Exception as exc:  # noqa: BLE001
                st.session_state.black_litterman = None
                st.error(f"Error en Black-Litterman: {exc}")

    bl = st.session_state.get("black_litterman")
    if not bl:
        st.info("Edita las views y pulsa **Calcular Black-Litterman**.")
        st.stop()

    bl_stats = bl["bl_stats"]
    mk_stats = bl["markowitz_stats"]

    c1, c2, c3 = st.columns(3)
    with c1:
        show_metric("BL — Retorno esperado", format_percent(bl_stats["expected_return"]))
    with c2:
        show_metric("BL — Riesgo anual (σ)", format_percent(bl_stats["volatility"]))
    with c3:
        show_metric("BL — Sharpe", f"{bl_stats['sharpe']:.4f}")

    d1, d2, d3 = st.columns(3)
    with d1:
        show_metric("Markowitz — Retorno", format_percent(mk_stats["expected_return"]))
    with d2:
        show_metric("Markowitz — Riesgo (σ)", format_percent(mk_stats["volatility"]))
    with d3:
        show_metric("Markowitz — Sharpe", f"{mk_stats['sharpe']:.4f}")

    st.markdown("##### Retornos: histórico vs equilibrio vs Black-Litterman")
    st.dataframe(
        theme_styler(
            bl["returns_table"],
            {
                "Retorno historico": "{:.2%}",
                "Equilibrio (pi)": "{:.2%}",
                "Retorno Black-Litterman": "{:.2%}",
            },
        ),
        use_container_width=True,
    )

    st.markdown("##### Pesos: mercado vs Markowitz vs Black-Litterman")
    st.dataframe(
        theme_styler(
            bl["weights_table"],
            {
                "Peso mercado": "{:.2%}",
                "Máx. Sharpe (Markowitz)": "{:.2%}",
                "Máx. Sharpe (Black-Litterman)": "{:.2%}",
            },
        ),
        use_container_width=True,
    )

    w1, w2 = st.columns(2)
    with w1:
        st.plotly_chart(
            weights_bar_chart(
                bl["weights_markowitz"],
                title="Máx. Sharpe Markowitz",
            ),
            use_container_width=True,
        )
    with w2:
        st.plotly_chart(
            weights_bar_chart(
                bl["weights_bl"],
                title="Máx. Sharpe Black-Litterman",
            ),
            use_container_width=True,
        )

    with st.expander("Matrices P, Q y Ω (views)"):
        st.write("**P** (pick matrix)")
        st.dataframe(theme_styler(bl["P"], "{:.2f}"), use_container_width=True)
        st.write("**Q** (retornos de las views)")
        st.dataframe(
            theme_styler(bl["Q"].rename("Q").to_frame(), "{:.2%}"),
            use_container_width=True,
        )
        st.write("**Ω** (incertidumbre de views)")
        st.dataframe(theme_styler(bl["omega"], "{:.6f}"), use_container_width=True)
