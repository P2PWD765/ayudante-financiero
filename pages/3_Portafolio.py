"""Página Portafolio — grupos de tickers, análisis y clasificación."""

from __future__ import annotations

import streamlit as st

import config
from modules.charts import correlation_heatmap, covariance_heatmap
from modules.classification import market_from_benchmark, validate_yahoo_ticker
from modules.helpers import (
    INDICATOR_HELP,
    apply_theme,
    format_percent,
    show_metric,
    theme_styler,
)
from modules.portfolio import portfolios_summary_table
from modules.state import (
    add_analysis_group,
    init_session_state,
    remove_analysis_group,
    render_active_group_selector,
    run_groups_analysis,
)
from modules.tradingview import render_tradingview_chart, yahoo_to_tradingview

st.set_page_config(page_title="Portafolio", layout="wide")
apply_theme()
init_session_state()

st.title("Portafolio")
st.caption(
    "Define una o más filas de tickers (hasta "
    f"{config.MAX_ANALYSIS_GROUPS}). Cada fila tiene su **benchmark** "
    "(identifica el mercado: p. ej. ^N225 → Japón). "
    "Se generan siempre 3 portafolios por grupo: Equiponderado, Máximo Sharpe y Mínima varianza."
)

# ---------------------------------------------------------------------------
# Filas de grupos
# ---------------------------------------------------------------------------
st.subheader("Grupos de tickers")
groups = st.session_state.analysis_groups

for i, group in enumerate(list(groups)):
    with st.container():
        h1, h2, h3 = st.columns([3, 2, 1])
        with h1:
            group["name"] = st.text_input(
                "Nombre del grupo",
                value=group.get("name", f"Grupo {i + 1}"),
                key=f"grp_name_{group['id']}",
            )
        with h2:
            group["benchmark"] = st.text_input(
                "Benchmark (Yahoo)",
                value=group.get("benchmark", config.DEFAULT_BENCHMARK),
                key=f"grp_bench_{group['id']}",
                help="Ej. ^GSPC, ^N225, ^IXIC. Define el mercado del grupo.",
            ).strip().upper() or config.DEFAULT_BENCHMARK
        with h3:
            group["enabled"] = st.checkbox(
                "Activo",
                value=group.get("enabled", True),
                key=f"grp_en_{group['id']}",
            )
            market = market_from_benchmark(group["benchmark"])
            st.caption(f"Mercado: **{market}**")

        group["tickers_input"] = st.text_input(
            "Tickers (separados por coma)",
            value=group.get("tickers_input", ""),
            key=f"grp_tickers_{group['id']}",
            help="Ejemplo: MSFT, GOOGL, AMZN  ·  Japón: 7203.T, 6758.T",
        )

        if len(groups) > 1:
            if st.button("Eliminar esta fila", key=f"grp_del_{group['id']}"):
                remove_analysis_group(group["id"])
                st.rerun()

st.session_state.analysis_groups = groups

b1, b2 = st.columns(2)
with b1:
    if st.button("＋ Añadir fila de tickers"):
        created = add_analysis_group(
            benchmark=st.session_state.get("benchmark") or config.DEFAULT_BENCHMARK
        )
        if created is None:
            st.warning(
                f"Máximo {config.MAX_ANALYSIS_GROUPS} grupos en esta versión."
            )
        else:
            st.rerun()
with b2:
    st.caption(
        "Periodo, Rf y capital se toman de **Configuración** "
        f"(periodo={st.session_state.period}, Rf={format_percent(st.session_state.risk_free_rate)})."
    )

# ---------------------------------------------------------------------------
# Nota + validador Yahoo
# ---------------------------------------------------------------------------
st.info(
    "**Nota Yahoo Finance:** usa símbolos válidos en Yahoo "
    "(ej. `MSFT`, `BRK-B`, `7203.T`, `^GSPC`). "
    "Sepáralos por coma. Si un ticker no existe, ese grupo puede fallar. "
    "El **benchmark de la fila** identifica el mercado del grupo "
    "(Nikkei → Japón, S&P → EE.UU., etc.), aunque la empresa cotice en otra bolsa."
)

with st.expander("Probar ticker en Yahoo Finance"):
    test_raw = st.text_input("Ticker a validar", value="MSFT", key="yahoo_test_ticker")
    if st.button("Validar ticker"):
        result = validate_yahoo_ticker(test_raw)
        if result["ok"]:
            st.success(result["message"])
        else:
            st.error(result["message"])

c1, c2, c3 = st.columns(3)
with c1:
    show_metric("Periodo histórico", st.session_state.period, help_key="periodo")
with c2:
    show_metric(
        "Grupos definidos",
        len(st.session_state.analysis_groups),
        help_text="Filas de tickers configuradas (máx. "
        f"{config.MAX_ANALYSIS_GROUPS}).",
    )
with c3:
    show_metric(
        "Rf (tasa libre de riesgo)",
        format_percent(st.session_state.risk_free_rate),
        help_key="rf",
    )

analyze = st.button("Analizar portafolios", type="primary")

if analyze:
    with st.spinner("Descargando datos y construyendo portafolios por grupo..."):
        try:
            analyzed = run_groups_analysis()
            names = []
            for g in st.session_state.analysis_groups:
                if g["id"] in analyzed:
                    names.append(g.get("name", g["id"]))
            extra = ""
            if st.session_state.get("last_error"):
                extra = f" Avisos: {st.session_state.last_error}"
            st.success(
                "Análisis completado para: " + ", ".join(names) + "." + extra
            )
        except Exception as exc:  # noqa: BLE001
            st.session_state.analysis_ready = False
            st.session_state.last_error = str(exc)
            st.error(f"Error en el análisis: {exc}")

# ---------------------------------------------------------------------------
# Resultados del grupo activo
# ---------------------------------------------------------------------------
if st.session_state.get("analysis_ready") and st.session_state.get("portfolios"):
    render_active_group_selector(key="portfolio_active_group")

    st.subheader("Clasificación de activos")
    st.caption(
        "Mercado = vía benchmark del grupo · "
        "Sector / grupo industrial / industria = FinanceDatabase (fallback Yahoo). "
        "País (base datos) es solo referencia; el mercado del análisis lo marca el benchmark."
    )
    classification = st.session_state.get("classification")
    if classification is None or getattr(classification, "empty", True):
        st.warning("Sin clasificación. Vuelve a analizar.")
    else:
        st.dataframe(theme_styler(classification), use_container_width=True)

    st.subheader("Resumen de los 3 portafolios")
    st.caption(
        "Rendimiento = retorno esperado · Desviacion E. = riesgo (σ) · "
        "Sharpe / Treynor / Jensen / Beta = ratios de desempeño "
        f"(Beta vs benchmark `{st.session_state.benchmark}`)."
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
                "VaR 95% paramétrico (mensual)": "{:.2%}",
                "VaR 95% histórico (mensual)": "{:.2%}",
                "CVaR 95% (mensual)": "{:.2%}",
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
                    "Beta individual de cada activo vs el benchmark del grupo."
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

    st.subheader("TradingView — activo seleccionado")
    st.caption("Gráfico interactivo del ticker elegido (mismo widget que en Dashboard).")
    tickers_ready = list(st.session_state.tickers)
    sel = st.selectbox(
        "Activo",
        tickers_ready,
        key="portfolio_tradingview_ticker",
    )
    st.caption(f"Yahoo `{sel}` → TradingView `{yahoo_to_tradingview(sel)}`")
    try:
        render_tradingview_chart(sel, watchlist=tickers_ready)
    except Exception as exc:  # noqa: BLE001
        st.warning(f"No se pudo cargar TradingView: {exc}")
else:
    st.info("Define grupos y pulsa **Analizar portafolios** para generar resultados.")
