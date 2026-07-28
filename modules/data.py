"""
Obtención y limpieza de datos financieros.

Fuente inicial: Yahoo Finance (yfinance).
Responsabilidades:
- Descargar precios históricos.
- Limpiar y alinear series.
- Obtener fundamentales (sin ROIC en v1).
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import yfinance as yf

import config
from modules.helpers import safe_get, validate_tickers


def download_prices(
    tickers: Iterable[str],
    period: str | None = None,
    interval: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Descarga precios históricos ajustados para uno o más tickers.

    Args:
        tickers: Símbolos a descargar (ej. ['AAPL', 'MSFT']).
        period: Periodo relativo de yfinance (ej. '5y'). Se ignora si hay start.
        interval: Frecuencia (ej. '1d').
        start: Fecha inicial opcional (YYYY-MM-DD).
        end: Fecha final opcional (YYYY-MM-DD).

    Returns:
        DataFrame con precios de cierre ajustados.
        Índice = fechas, columnas = tickers.

    Raises:
        ValueError: Si no hay tickers válidos o no se obtienen datos.
    """
    symbols = validate_tickers(tickers)
    period = period or config.DEFAULT_PERIOD
    interval = interval or config.DEFAULT_INTERVAL

    download_kwargs: dict = {
        "tickers": " ".join(symbols),
        "interval": interval,
        "auto_adjust": True,
        "progress": False,
        "threads": True,
    }

    if start:
        download_kwargs["start"] = start
        if end:
            download_kwargs["end"] = end
    else:
        download_kwargs["period"] = period

    raw = yf.download(**download_kwargs)

    if raw is None or raw.empty:
        raise ValueError(
            f"No se pudieron descargar precios para: {', '.join(symbols)}"
        )

    prices = _extract_close_prices(raw, symbols)
    return clean_price_data(prices)


def download_benchmark(
    benchmark: str | None = None,
    period: str | None = None,
    interval: str | None = None,
    start: str | None = None,
    end: str | None = None,
) -> pd.Series:
    """Descarga la serie de precios del benchmark.

    Args:
        benchmark: Símbolo del benchmark (default en config).
        period: Periodo relativo.
        interval: Frecuencia.
        start: Fecha inicial opcional.
        end: Fecha final opcional.

    Returns:
        Serie de precios del benchmark.
    """
    symbol = (benchmark or config.DEFAULT_BENCHMARK).strip().upper()
    prices = download_prices(
        tickers=[symbol],
        period=period,
        interval=interval,
        start=start,
        end=end,
    )
    return prices[symbol].rename(symbol)


def clean_price_data(prices: pd.DataFrame) -> pd.DataFrame:
    """Limpia precios: ordena fechas, elimina vacíos y alinea columnas.

    Args:
        prices: DataFrame de precios (fechas x tickers).

    Returns:
        DataFrame limpio, sin columnas totalmente vacías ni filas sin datos.

    Raises:
        ValueError: Si tras la limpieza no quedan datos útiles.
    """
    if prices is None or prices.empty:
        raise ValueError("El DataFrame de precios está vacío.")

    cleaned = prices.copy()
    cleaned = cleaned.sort_index()
    cleaned = cleaned.apply(pd.to_numeric, errors="coerce")
    cleaned = cleaned.dropna(axis=1, how="all")
    cleaned = cleaned.dropna(axis=0, how="all")

    # Solo elimina filas donde falte algún activo (alineación estricta).
    cleaned = cleaned.dropna(axis=0, how="any")

    if cleaned.empty:
        raise ValueError(
            "Tras la limpieza no quedaron precios válidos. "
            "Revisa tickers o el periodo solicitado."
        )

    cleaned.index = pd.to_datetime(cleaned.index)
    cleaned.index.name = "Date"
    return cleaned


def get_fundamentals(tickers: Iterable[str]) -> pd.DataFrame:
    """Obtiene fundamentales clave por ticker desde Yahoo Finance.

    Campos v1 (sin ROIC):
    - Market Cap
    - Enterprise Value
    - EV/EBITDA
    - P/S
    - ROA
    - ROE

    Args:
        tickers: Símbolos a consultar.

    Returns:
        DataFrame indexado por ticker con columnas legibles.
        Los campos faltantes quedan como NaN (no rompe la app).
    """
    symbols = validate_tickers(tickers)
    rows: list[dict] = []

    for symbol in symbols:
        row: dict = {"Ticker": symbol}
        try:
            info = yf.Ticker(symbol).info or {}
        except Exception:  # noqa: BLE001
            info = {}

        for field_key, field_label in config.FUNDAMENTAL_FIELDS.items():
            value = safe_get(info, field_key, default=pd.NA)
            row[field_label] = pd.to_numeric(value, errors="coerce")

        rows.append(row)

    fundamentals = pd.DataFrame(rows).set_index("Ticker")
    return fundamentals


def align_with_benchmark(
    prices: pd.DataFrame,
    benchmark: pd.Series,
) -> tuple[pd.DataFrame, pd.Series]:
    """Alinea precios de activos con el benchmark en las mismas fechas.

    Args:
        prices: Precios de activos.
        benchmark: Serie del benchmark.

    Returns:
        Tupla (precios_alineados, benchmark_alineado).

    Raises:
        ValueError: Si no hay fechas en común.
    """
    if prices.empty or benchmark.empty:
        raise ValueError("Precios o benchmark vacíos; no se pueden alinear.")

    bench = benchmark.copy()
    bench.name = bench.name or "Benchmark"

    combined = prices.join(bench, how="inner")
    if combined.empty:
        raise ValueError("No hay fechas en común entre activos y benchmark.")

    aligned_prices = combined[prices.columns]
    aligned_benchmark = combined[bench.name]
    return aligned_prices, aligned_benchmark


def _extract_close_prices(raw: pd.DataFrame, symbols: list[str]) -> pd.DataFrame:
    """Normaliza la salida de yfinance a un DataFrame de cierres.

    Args:
        raw: Resultado crudo de yf.download.
        symbols: Lista de tickers solicitados.

    Returns:
        DataFrame con una columna por ticker.
    """
    # Un solo ticker: columnas simples (Open, High, Low, Close, Volume).
    if not isinstance(raw.columns, pd.MultiIndex):
        if "Close" not in raw.columns:
            raise ValueError("La descarga no incluye columna 'Close'.")
        close = raw[["Close"]].copy()
        close.columns = [symbols[0]]
        return close

    # Varios tickers: MultiIndex (Price, Ticker) o (Ticker, Price).
    level0 = raw.columns.get_level_values(0)
    level1 = raw.columns.get_level_values(1)

    if "Close" in level0:
        close = raw["Close"].copy()
    elif "Close" in level1:
        close = raw.xs("Close", axis=1, level=1).copy()
    else:
        raise ValueError("No se encontró el nivel 'Close' en la descarga.")

    # Conserva solo columnas pedidas y en el mismo orden.
    available = [s for s in symbols if s in close.columns]
    missing = [s for s in symbols if s not in close.columns]

    if missing:
        raise ValueError(
            "Sin datos de precios para: "
            f"{', '.join(missing)}. Verifica que los tickers existan en Yahoo Finance."
        )

    return close[available]
