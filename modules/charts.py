"""
Gráficas del Dashboard Financiero (Plotly).

La UI solo llama a estas funciones; no construye figuras a mano.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import config


def _style_figure(fig: go.Figure) -> go.Figure:
    """Aplica la paleta Azul Dashboard a una figura Plotly."""
    c = config.COLORS
    fig.update_layout(
        paper_bgcolor=c["card"],
        plot_bgcolor=c["background"],
        font=dict(color=c["text"], size=12),
        title_font=dict(color=c["text"], size=16),
        colorway=config.CHART_COLORWAY,
        xaxis=dict(
            gridcolor="rgba(15, 23, 42, 0.08)",
            zerolinecolor="rgba(15, 23, 42, 0.20)",
            linecolor=c["text_muted"],
            tickfont=dict(color=c["text"]),
            title_font=dict(color=c["text"]),
        ),
        yaxis=dict(
            gridcolor="rgba(15, 23, 42, 0.08)",
            zerolinecolor="rgba(15, 23, 42, 0.20)",
            linecolor=c["text_muted"],
            tickfont=dict(color=c["text"]),
            title_font=dict(color=c["text"]),
        ),
        legend=dict(font=dict(color=c["text"])),
    )
    return fig


def correlation_heatmap(
    corr_matrix: pd.DataFrame,
    title: str = "Mapa de calor de correlaciones",
) -> go.Figure:
    """Genera un mapa de calor de la matriz de correlaciones.

    Args:
        corr_matrix: Matriz de correlación entre activos del portafolio.
        title: Título del gráfico.

    Returns:
        Figura Plotly lista para st.plotly_chart.
    """
    fig = px.imshow(
        corr_matrix,
        text_auto=".2f",
        aspect="auto",
        color_continuous_scale=config.HEATMAP_CORR,
        zmin=-1,
        zmax=1,
        title=title,
    )
    fig.update_traces(textfont=dict(color=config.COLORS["text"], size=11))
    fig.update_layout(
        coloraxis_colorbar_title="ρ",
        coloraxis_colorbar_tickfont_color=config.COLORS["text"],
        coloraxis_colorbar_title_font_color=config.COLORS["text"],
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)


def covariance_heatmap(
    cov_matrix: pd.DataFrame,
    title: str = "Mapa de calor de covarianzas",
) -> go.Figure:
    """Genera un mapa de calor de la matriz de covarianzas.

    Args:
        cov_matrix: Matriz de covarianza entre activos.
        title: Título del gráfico.

    Returns:
        Figura Plotly.
    """
    fig = px.imshow(
        cov_matrix,
        text_auto=".4f",
        aspect="auto",
        color_continuous_scale=config.HEATMAP_COV,
        title=title,
    )
    fig.update_traces(textfont=dict(color=config.COLORS["text"], size=11))
    fig.update_layout(
        coloraxis_colorbar_title="Cov",
        coloraxis_colorbar_tickfont_color=config.COLORS["text"],
        coloraxis_colorbar_title_font_color=config.COLORS["text"],
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)


def weights_bar_chart(
    weights: pd.Series,
    title: str = "Distribución de pesos",
) -> go.Figure:
    """Gráfico de barras con los pesos del portafolio.

    Args:
        weights: Serie de pesos por ticker.
        title: Título del gráfico.

    Returns:
        Figura Plotly.
    """
    data = weights.sort_values(ascending=False)
    fig = go.Figure(
        data=[
            go.Bar(
                x=data.index.astype(str),
                y=data.values,
                marker_color=config.COLORS["primary"],
                marker_line=dict(width=0),
                text=[f"{v:.1%}" for v in data.values],
                textposition="outside",
                textfont=dict(color=config.COLORS["text"]),
            )
        ]
    )
    fig.update_layout(
        title=title,
        yaxis_title="Peso",
        xaxis_title="Ticker",
        yaxis_tickformat=".0%",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)


def efficient_frontier_chart(
    frontier: pd.DataFrame,
    cal: pd.DataFrame | None = None,
    assets: pd.DataFrame | None = None,
    min_variance: dict | None = None,
    max_sharpe: dict | None = None,
    risk_free_rate: float | None = None,
    title: str = "Frontera eficiente y CAL",
) -> go.Figure:
    """Grafica frontera eficiente, CAL, activos y portafolios clave.

    Args:
        frontier: DataFrame con volatility / expected_return.
        cal: DataFrame de la Capital Allocation Line.
        assets: DataFrame de activos individuales (volatility, expected_return).
        min_variance: Dict con volatility / expected_return del min-var.
        max_sharpe: Dict con volatility / expected_return del max Sharpe.
        risk_free_rate: Rf para marcar el punto (0, Rf).
        title: Título del gráfico.

    Returns:
        Figura Plotly.
    """
    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=frontier["volatility"],
            y=frontier["expected_return"],
            mode="lines+markers",
            name="Frontera eficiente",
            line=dict(color=config.COLORS["primary"], width=3),
            marker=dict(size=6, color=config.COLORS["primary"]),
        )
    )

    if cal is not None and not cal.empty:
        fig.add_trace(
            go.Scatter(
                x=cal["volatility"],
                y=cal["expected_return"],
                mode="lines",
                name="CAL",
                line=dict(color=config.COLORS["secondary"], width=2.5, dash="dash"),
            )
        )

    if assets is not None and not assets.empty:
        fig.add_trace(
            go.Scatter(
                x=assets["volatility"],
                y=assets["expected_return"],
                mode="markers+text",
                name="Activos",
                text=assets.index.astype(str),
                textposition="top center",
                textfont=dict(color=config.COLORS["text"], size=11),
                marker=dict(
                    size=10,
                    color=config.COLORS["neutral"],
                    symbol="diamond",
                    line=dict(width=1, color=config.COLORS["text"]),
                ),
            )
        )

    if min_variance is not None:
        fig.add_trace(
            go.Scatter(
                x=[min_variance["volatility"]],
                y=[min_variance["expected_return"]],
                mode="markers",
                name="Mínima varianza",
                marker=dict(
                    size=14,
                    color=config.COLORS["danger"],
                    symbol="x",
                    line=dict(width=2, color=config.COLORS["danger"]),
                ),
            )
        )

    if max_sharpe is not None:
        fig.add_trace(
            go.Scatter(
                x=[max_sharpe["volatility"]],
                y=[max_sharpe["expected_return"]],
                mode="markers",
                name="Máximo Sharpe",
                marker=dict(
                    size=14,
                    color=config.COLORS["primary"],
                    symbol="star",
                    line=dict(width=1, color=config.COLORS["on_primary"]),
                ),
            )
        )

    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[rf],
            mode="markers",
            name="Rf",
            marker=dict(size=12, color=config.COLORS["text"], symbol="circle"),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Volatilidad (riesgo)",
        yaxis_title="Retorno esperado",
        xaxis_tickformat=".1%",
        yaxis_tickformat=".1%",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=40, t=80, b=40),
    )
    return _style_figure(fig)


def capital_allocation_line_chart(
    cal: pd.DataFrame,
    max_sharpe: dict | None = None,
    risk_free_rate: float | None = None,
    title: str = "Capital Allocation Line (CAL)",
) -> go.Figure:
    """Grafica únicamente la CAL con Rf y portafolio tangencial.

    Args:
        cal: DataFrame de la CAL.
        max_sharpe: Punto tangencial.
        risk_free_rate: Rf.
        title: Título.

    Returns:
        Figura Plotly.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=cal["volatility"],
            y=cal["expected_return"],
            mode="lines+markers",
            name="CAL",
            line=dict(color=config.COLORS["secondary"], width=3),
        )
    )

    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    fig.add_trace(
        go.Scatter(
            x=[0.0],
            y=[rf],
            mode="markers",
            name="Rf",
            marker=dict(size=12, color=config.COLORS["text"]),
        )
    )

    if max_sharpe is not None:
        fig.add_trace(
            go.Scatter(
                x=[max_sharpe["volatility"]],
                y=[max_sharpe["expected_return"]],
                mode="markers",
                name="Tangencial (Max Sharpe)",
                marker=dict(size=14, color=config.COLORS["primary"], symbol="star"),
            )
        )

    fig.update_layout(
        title=title,
        xaxis_title="Volatilidad",
        yaxis_title="Retorno esperado",
        xaxis_tickformat=".1%",
        yaxis_tickformat=".1%",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)


def price_evolution_chart(
    prices: pd.DataFrame,
    title: str = "Evolución de precios",
    normalize: bool = False,
) -> go.Figure:
    """Grafica la evolución de precios de uno o más activos.

    Args:
        prices: DataFrame de precios (fechas x tickers).
        title: Título del gráfico.
        normalize: Si True, reescala cada serie a base 100.

    Returns:
        Figura Plotly.
    """
    data = prices.copy()
    if normalize:
        data = data / data.iloc[0] * 100.0
        y_title = "Precio (base 100)"
    else:
        y_title = "Precio"

    fig = go.Figure()
    for col in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[col],
                mode="lines",
                name=str(col),
                line=dict(width=2.5),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title=y_title,
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _style_figure(fig)


def returns_chart(
    returns: pd.DataFrame | pd.Series,
    title: str = "Rendimientos",
) -> go.Figure:
    """Grafica la serie de rendimientos.

    Args:
        returns: Serie o DataFrame de rendimientos.
        title: Título del gráfico.

    Returns:
        Figura Plotly.
    """
    data = returns.to_frame() if isinstance(returns, pd.Series) else returns
    fig = go.Figure()
    for col in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[col],
                mode="lines",
                name=str(col),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Rendimiento",
        yaxis_tickformat=".1%",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _style_figure(fig)


def cumulative_returns_chart(
    cumulative: pd.DataFrame | pd.Series,
    title: str = "Rendimiento acumulado",
) -> go.Figure:
    """Grafica el rendimiento acumulado.

    Args:
        cumulative: Serie/DataFrame de rendimiento acumulado (decimal).
        title: Título.

    Returns:
        Figura Plotly.
    """
    data = cumulative.to_frame() if isinstance(cumulative, pd.Series) else cumulative
    fig = go.Figure()
    for col in data.columns:
        fig.add_trace(
            go.Scatter(
                x=data.index,
                y=data[col],
                mode="lines",
                name=str(col),
            )
        )
    fig.update_layout(
        title=title,
        xaxis_title="Fecha",
        yaxis_title="Rendimiento acumulado",
        yaxis_tickformat=".1%",
        margin=dict(l=40, r=40, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return _style_figure(fig)


def risk_return_scatter(
    assets: pd.DataFrame,
    portfolios: dict[str, dict] | None = None,
    title: str = "Riesgo vs rendimiento",
) -> go.Figure:
    """Scatter de riesgo vs retorno para activos y portafolios.

    Args:
        assets: DataFrame con columnas volatility / expected_return.
        portfolios: Dict opcional {nombre: {volatility, expected_return}}.
        title: Título.

    Returns:
        Figura Plotly.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=assets["volatility"],
            y=assets["expected_return"],
            mode="markers+text",
            name="Activos",
            text=assets.index.astype(str),
            textposition="top center",
            textfont=dict(color=config.COLORS["text"], size=11),
            marker=dict(size=11, color=config.COLORS["neutral"], symbol="diamond"),
        )
    )

    if portfolios:
        for i, (name, perf) in enumerate(portfolios.items()):
            color = config.CHART_COLORWAY[i % len(config.CHART_COLORWAY)]
            fig.add_trace(
                go.Scatter(
                    x=[perf["volatility"]],
                    y=[perf.get("expected_return", perf.get("rendimiento"))],
                    mode="markers+text",
                    name=name,
                    text=[name],
                    textposition="bottom center",
                    textfont=dict(color=config.COLORS["text"], size=11),
                    marker=dict(size=13, symbol="star", color=color),
                )
            )

    fig.update_layout(
        title=title,
        xaxis_title="Volatilidad (riesgo)",
        yaxis_title="Retorno esperado",
        xaxis_tickformat=".1%",
        yaxis_tickformat=".1%",
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)


def comparison_metrics_chart(
    summary: pd.DataFrame,
    metric_col: str,
    yahoo_col: str | None = None,
    title: str | None = None,
) -> go.Figure:
    """Barras comparando métrica calculada vs Yahoo (si existe).

    Args:
        summary: Tabla con métricas por ticker/portafolio.
        metric_col: Columna del valor calculado.
        yahoo_col: Columna del valor Yahoo (opcional).
        title: Título.

    Returns:
        Figura Plotly.
    """
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=summary.index.astype(str),
            y=summary[metric_col],
            name="Calculado",
            marker_color=config.COLORS["primary"],
            marker_line=dict(width=0),
        )
    )
    if yahoo_col and yahoo_col in summary.columns:
        fig.add_trace(
            go.Bar(
                x=summary.index.astype(str),
                y=summary[yahoo_col],
                name="Yahoo",
                marker_color=config.COLORS["secondary"],
                marker_line=dict(width=0),
            )
        )

    fig.update_layout(
        title=title or f"Comparación: {metric_col}",
        barmode="group",
        xaxis_title="",
        yaxis_title=metric_col,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    return _style_figure(fig)
