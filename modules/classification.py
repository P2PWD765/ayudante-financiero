"""
Clasificación de activos: sector, industria y mercado.

- Sector / industria / industry_group: FinanceDatabase (fallback Yahoo).
- Mercado/país del grupo: se toma del **benchmark** del grupo
  (regla de producto: Nikkei → Japón, S&P → EE.UU., etc.).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import pandas as pd

import config


def market_from_benchmark(benchmark: str) -> str:
    """Devuelve la etiqueta de mercado/país asociada al benchmark.

    Args:
        benchmark: Símbolo Yahoo del índice (ej. ^N225).

    Returns:
        Nombre de mercado o 'Desconocido' si no está en el mapa.
    """
    key = (benchmark or "").strip().upper()
    return config.BENCHMARK_MARKET_MAP.get(key, f"Desconocido ({key or '—'})")


@lru_cache(maxsize=1)
def _equities_frame() -> pd.DataFrame:
    """Carga (una vez) el catálogo de equities de FinanceDatabase."""
    import financedatabase as fd

    equities = fd.Equities()
    data = equities.data
    if data is None or getattr(data, "empty", True):
        return pd.DataFrame()
    return data


def lookup_equity_profile(ticker: str) -> dict[str, Any]:
    """Busca perfil en FinanceDatabase; si falta, intenta Yahoo info.

    Args:
        ticker: Símbolo Yahoo.

    Returns:
        Dict con name, sector, industry_group, industry, country_db, exchange.
    """
    symbol = (ticker or "").strip().upper()
    empty = {
        "name": None,
        "sector": None,
        "industry_group": None,
        "industry": None,
        "country_db": None,
        "exchange": None,
        "source": None,
    }
    if not symbol:
        return empty

    frame = _equities_frame()
    if not frame.empty and symbol in frame.index:
        row = frame.loc[symbol]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        return {
            "name": row.get("name"),
            "sector": row.get("sector"),
            "industry_group": row.get("industry_group"),
            "industry": row.get("industry"),
            "country_db": row.get("country"),
            "exchange": row.get("exchange"),
            "source": "FinanceDatabase",
        }

    # Fallback Yahoo
    try:
        import yfinance as yf
        from modules.helpers import safe_get

        info = yf.Ticker(symbol).info or {}
        return {
            "name": safe_get(info, "shortName") or safe_get(info, "longName"),
            "sector": safe_get(info, "sector"),
            "industry_group": safe_get(info, "industryDisp") or safe_get(info, "industry"),
            "industry": safe_get(info, "industry"),
            "country_db": safe_get(info, "country"),
            "exchange": safe_get(info, "exchange"),
            "source": "Yahoo",
        }
    except Exception:  # noqa: BLE001
        return {**empty, "source": None}


def classify_tickers(
    tickers: list[str],
    benchmark: str,
) -> pd.DataFrame:
    """Clasifica tickers: mercado vía benchmark + sector/industria vía DB.

    Args:
        tickers: Lista de símbolos.
        benchmark: Benchmark del grupo (identificador de mercado).

    Returns:
        DataFrame indexado por ticker.
    """
    market = market_from_benchmark(benchmark)
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        profile = lookup_equity_profile(ticker)
        rows.append(
            {
                "Ticker": ticker,
                "Mercado (via benchmark)": market,
                "Benchmark": (benchmark or "").strip().upper(),
                "Nombre": profile.get("name") or "N/A",
                "Sector": profile.get("sector") or "N/A",
                "Grupo industrial": profile.get("industry_group") or "N/A",
                "Industria": profile.get("industry") or "N/A",
                "País (base datos)": profile.get("country_db") or "N/A",
                "Exchange": profile.get("exchange") or "N/A",
                "Fuente metadatos": profile.get("source") or "N/A",
            }
        )
    return pd.DataFrame(rows).set_index("Ticker")


def validate_yahoo_ticker(symbol: str) -> dict[str, Any]:
    """Comprueba si un ticker parece válido en Yahoo Finance.

    Args:
        symbol: Ticker a probar.

    Returns:
        Dict con ok (bool), symbol, message, name opcional.
    """
    ticker = (symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "symbol": ticker, "message": "Ticker vacío.", "name": None}

    try:
        import yfinance as yf

        info = yf.Ticker(ticker).info or {}
        name = info.get("shortName") or info.get("longName")
        # Yahoo a veces devuelve {} o solo quoteType sin precio.
        has_hint = bool(name) or bool(info.get("regularMarketPrice")) or bool(
            info.get("exchange")
        )
        if not has_hint:
            hist = yf.Ticker(ticker).history(period="5d")
            if hist is None or hist.empty:
                return {
                    "ok": False,
                    "symbol": ticker,
                    "message": "No encontrado en Yahoo Finance.",
                    "name": None,
                }
            return {
                "ok": True,
                "symbol": ticker,
                "message": "Válido (serie de precios reciente).",
                "name": name,
            }
        return {
            "ok": True,
            "symbol": ticker,
            "message": f"Válido: {name}" if name else "Válido en Yahoo Finance.",
            "name": name,
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "symbol": ticker,
            "message": f"Error al consultar Yahoo: {exc}",
            "name": None,
        }
