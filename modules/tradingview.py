"""
Integración TradingView (widget embebido, sin API key).

Convierte tickers de Yahoo Finance a símbolos TradingView
y genera el HTML del Advanced Chart.
"""

from __future__ import annotations

import json
from typing import Iterable

import streamlit.components.v1 as components

import config


def yahoo_to_tradingview(symbol: str) -> str:
    """Mapea un ticker Yahoo Finance a un símbolo TradingView.

    Args:
        symbol: Ticker Yahoo (ej. MSFT, BRK-B, ^GSPC).

    Returns:
        Símbolo para el widget (ej. MSFT, BRK.B, SP:SPX).
    """
    raw = (symbol or "").strip().upper()
    if not raw:
        raise ValueError("El símbolo TradingView no puede estar vacío.")

    mapped = config.TRADINGVIEW_SYMBOL_MAP.get(raw)
    if mapped:
        return mapped

    # Yahoo usa guion en clases de acciones (BRK-B); TradingView usa punto.
    normalized = raw.replace("-", ".")

    # Índices Yahoo suelen empezar con ^; sin mapa explícito, quitar ^.
    if normalized.startswith("^"):
        normalized = normalized[1:]

    return normalized


def tradingview_chart_html(
    symbol: str,
    *,
    height: int | None = None,
    interval: str | None = None,
    theme: str | None = None,
    watchlist: Iterable[str] | None = None,
) -> str:
    """Construye el HTML del Advanced Chart de TradingView.

    Args:
        symbol: Símbolo TradingView (ya mapeado).
        height: Alto del iframe/contenedor en px.
        interval: Intervalo del gráfico (D, W, M, etc.).
        theme: light / dark.
        watchlist: Lista opcional de símbolos para la barra lateral.

    Returns:
        HTML listo para components.html.
    """
    height = int(height or config.TRADINGVIEW_HEIGHT)
    interval = interval or config.TRADINGVIEW_INTERVAL
    theme = theme or config.TRADINGVIEW_THEME

    widget_cfg: dict = {
        "autosize": True,
        "symbol": symbol,
        "interval": interval,
        "timezone": "Etc/UTC",
        "theme": theme,
        "style": "1",
        "locale": "es",
        "backgroundColor": config.COLORS["card"],
        "gridColor": "rgba(15, 23, 42, 0.08)",
        "hide_top_toolbar": False,
        "hide_legend": False,
        "allow_symbol_change": True,
        "save_image": False,
        "calendar": False,
        "support_host": "https://www.tradingview.com",
        "withdateranges": True,
        "hide_side_toolbar": False,
    }
    if watchlist:
        widget_cfg["watchlist"] = [yahoo_to_tradingview(s) for s in watchlist]

    cfg_json = json.dumps(widget_cfg, ensure_ascii=False)
    # El script de TradingView lee el JSON como texto hijo del <script>.
    return f"""
<div class="tradingview-widget-container" style="height:{height}px;width:100%;">
  <div class="tradingview-widget-container__widget"
       style="height:calc(100% - 32px);width:100%;"></div>
  <div class="tradingview-widget-copyright">
    <a href="https://www.tradingview.com/symbols/{symbol.replace(':', '-')}/"
       rel="noopener nofollow" target="_blank">
      <span style="color:{config.COLORS['primary']};">{symbol}</span>
    </a>
    <span> por TradingView</span>
  </div>
  <script type="text/javascript"
          src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js"
          async>
  {cfg_json}
  </script>
</div>
"""


def render_tradingview_chart(
    yahoo_symbol: str,
    *,
    height: int | None = None,
    watchlist: Iterable[str] | None = None,
) -> str:
    """Renderiza el widget TradingView en Streamlit.

    Args:
        yahoo_symbol: Ticker como en Yahoo / session_state.
        height: Alto del componente.
        watchlist: Otros tickers del análisis (opcional).

    Returns:
        Símbolo TradingView usado (para captions).
    """
    tv_symbol = yahoo_to_tradingview(yahoo_symbol)
    height = int(height or config.TRADINGVIEW_HEIGHT)
    html = tradingview_chart_html(
        tv_symbol,
        height=height,
        watchlist=watchlist,
    )
    components.html(html, height=height + 40, scrolling=False)
    return tv_symbol
