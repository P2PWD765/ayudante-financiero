"""
Construcción y evaluación de portafolios.

Regla de producto (v1):
Para cualquier conjunto de tickers el programa genera siempre 3 portafolios:
1) Equiponderado
2) Máximo Sharpe
3) Mínima varianza
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

import config
from modules import metrics
from modules.helpers import validate_tickers
from modules.optimization import maximum_sharpe_weights, minimum_variance_weights


PORTFOLIO_EQUAL_WEIGHT = "Equiponderado"
PORTFOLIO_MAX_SHARPE = "Máximo Sharpe"
PORTFOLIO_MIN_VARIANCE = "Mínima varianza"

STANDARD_PORTFOLIO_NAMES = (
    PORTFOLIO_EQUAL_WEIGHT,
    PORTFOLIO_MAX_SHARPE,
    PORTFOLIO_MIN_VARIANCE,
)


def equal_weights(tickers: Iterable[str]) -> pd.Series:
    """Crea pesos equiponderados (1/n) para los tickers dados."""
    symbols = validate_tickers(tickers)
    n = len(symbols)
    return pd.Series(np.full(n, 1.0 / n), index=symbols, name="weight")


def normalize_weights(weights: pd.Series | dict[str, float]) -> pd.Series:
    """Valida y normaliza pesos para que sumen 1."""
    series = pd.Series(weights, dtype=float).dropna()
    series.index = [str(i).strip().upper() for i in series.index]
    series = series[series.index != ""]

    if series.empty:
        raise ValueError("Debes indicar al menos un peso válido.")
    if (series < 0).any():
        raise ValueError("Los pesos no pueden ser negativos (long-only en v1).")

    total = float(series.sum())
    if total <= 0:
        raise ValueError("La suma de pesos debe ser mayor que cero.")

    normalized = series / total
    normalized.name = "weight"
    return normalized


def create_portfolio(name: str, weights: pd.Series | dict[str, float]) -> dict:
    """Crea un objeto portafolio con nombre y pesos."""
    w = normalize_weights(weights)
    return {"name": name, "tickers": list(w.index), "weights": w}


def portfolio_returns(asset_returns: pd.DataFrame, weights: pd.Series) -> pd.Series:
    """Serie de rendimientos del portafolio: R_p,t = sum_i w_i R_i,t."""
    w = normalize_weights(weights)
    aligned = asset_returns[w.index].dropna(how="any")
    return aligned.mul(w, axis=1).sum(axis=1).rename("portfolio")


def portfolio_expected_return(expected_returns: pd.Series, weights: pd.Series) -> float:
    """Retorno esperado del portafolio: w' μ."""
    w = normalize_weights(weights)
    mu = expected_returns.reindex(w.index).astype(float)
    if mu.isna().any():
        missing = mu[mu.isna()].index.tolist()
        raise ValueError(f"Faltan retornos esperados para: {', '.join(missing)}")
    return float(w @ mu)


def portfolio_variance(cov_matrix: pd.DataFrame, weights: pd.Series) -> float:
    """Varianza del portafolio: w' Σ w."""
    w = normalize_weights(weights)
    cov = cov_matrix.reindex(index=w.index, columns=w.index)
    if cov.isna().any().any():
        raise ValueError("La matriz de covarianzas tiene valores faltantes.")
    return float(w.values @ cov.values @ w.values)


def portfolio_volatility(cov_matrix: pd.DataFrame, weights: pd.Series) -> float:
    """Volatilidad del portafolio: sqrt(w' Σ w)."""
    return float(np.sqrt(portfolio_variance(cov_matrix, weights)))


def portfolio_sharpe(
    expected_return: float,
    volatility: float,
    risk_free_rate: float | None = None,
) -> float:
    """Sharpe del portafolio: (Rp - Rf) / sigma_p."""
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    if volatility == 0 or pd.isna(volatility):
        return float("nan")
    return float((expected_return - rf) / volatility)


def portfolio_value(capital: float, weights: pd.Series) -> pd.Series:
    """Asigna capital a cada activo según los pesos."""
    if capital < 0:
        raise ValueError("El capital no puede ser negativo.")
    w = normalize_weights(weights)
    return (w * capital).rename("value")


def evaluate_portfolio(name: str, weights: pd.Series, **kwargs) -> dict:
    """Evalúa un portafolio con indicadores mensuales y anuales.

    kwargs soportados:
    - expected_returns (anual) / expected_returns_annual
    - cov_matrix (anual) / cov_matrix_annual
    - expected_returns_monthly / cov_matrix_monthly (opcionales)
    - asset_returns / asset_returns_monthly (mensuales)
    - benchmark_returns / benchmark_returns_monthly (mensuales)
    - risk_free_rate, capital, correlation
    """
    mu_a = kwargs.get("expected_returns_annual", kwargs.get("expected_returns"))
    cov_a = kwargs.get("cov_matrix_annual", kwargs.get("cov_matrix"))
    mu_m = kwargs.get("expected_returns_monthly")
    cov_m = kwargs.get("cov_matrix_monthly")
    asset_m = kwargs.get("asset_returns_monthly", kwargs.get("asset_returns"))
    bench_m = kwargs.get(
        "benchmark_returns_monthly",
        kwargs.get("benchmark_returns"),
    )
    risk_free_rate = kwargs.get("risk_free_rate")
    capital = kwargs.get("capital")
    correlation = kwargs.get("correlation")

    if mu_a is None or cov_a is None:
        raise ValueError("Faltan retornos esperados o covarianzas para evaluar.")

    # Si asset_returns viene mensual, preferir μ/Σ estimados de esa serie.
    if asset_m is not None and not getattr(asset_m, "empty", True):
        if mu_m is None:
            mu_m = asset_m.mean()
        if cov_m is None:
            cov_m = asset_m.cov(ddof=1)

    if mu_m is None:
        mu_m = mu_a / config.MONTHS_PER_YEAR
    if cov_m is None:
        cov_m = cov_a / config.MONTHS_PER_YEAR

    w = normalize_weights(weights)
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate

    ret_m = portfolio_expected_return(mu_m, w)
    var_m = portfolio_variance(cov_m, w)
    vol_m = float(np.sqrt(var_m))

    ret_a = portfolio_expected_return(mu_a, w)
    var_a = portfolio_variance(cov_a, w)
    vol_a = float(np.sqrt(var_a))
    sharpe = portfolio_sharpe(ret_a, vol_a, risk_free_rate=rf)

    cov_assets = cov_m.reindex(index=w.index, columns=w.index)
    if correlation is not None:
        corr_assets = correlation.reindex(index=w.index, columns=w.index)
    elif asset_m is not None:
        corr_assets = metrics.correlation_matrix(asset_m[w.index])
    else:
        std = np.sqrt(np.diag(cov_assets.values))
        denom = np.outer(std, std)
        with np.errstate(divide="ignore", invalid="ignore"):
            corr_values = np.divide(cov_assets.values, denom)
        corr_assets = pd.DataFrame(
            corr_values,
            index=cov_assets.index,
            columns=cov_assets.columns,
        )

    beta_value = float("nan")
    jensen_value = float("nan")
    treynor_value = float("nan")
    asset_betas: dict[str, float] = {}
    portfolio_rets = None

    if asset_m is not None and bench_m is not None:
        portfolio_rets = portfolio_returns(asset_m, w)
        for ticker in w.index:
            asset_betas[ticker] = metrics.beta(asset_m[ticker], bench_m)
        beta_value = float(sum(w[t] * asset_betas[t] for t in w.index))
        jensen_value = metrics.jensen_alpha(
            portfolio_rets,
            bench_m,
            risk_free_rate=rf,
            periods_per_year=config.MONTHS_PER_YEAR,
        )
        treynor_value = metrics.treynor_ratio(
            expected_return=ret_a,
            beta_value=beta_value,
            risk_free_rate=rf,
        )

    result = {
        "name": name,
        "tickers": list(w.index),
        "weights": w,
        "asset_betas": pd.Series(asset_betas, dtype=float) if asset_betas else None,
        "rendimiento_mensual": ret_m,
        "varianza_mensual": var_m,
        "desviacion_estandar_mensual": vol_m,
        "rendimiento": ret_a,
        "rendimiento_anual": ret_a,
        "varianza": var_a,
        "varianza_anual": var_a,
        "desviacion_estandar": vol_a,
        "desviacion_estandar_anual": vol_a,
        "beta": beta_value,
        "sharpe": sharpe,
        "treynor": treynor_value,
        "jensen": jensen_value,
        "expected_return": ret_a,
        "variance": var_a,
        "volatility": vol_a,
        "covariance_matrix": cov_assets,
        "correlation_matrix": corr_assets,
        "returns": portfolio_rets,
        "rf_monthly": rf / config.MONTHS_PER_YEAR,
    }
    if capital is not None:
        result["value_by_ticker"] = portfolio_value(capital, w)
        result["capital"] = capital
    return result


def estimate_annual_inputs(prices: pd.DataFrame) -> tuple[pd.Series, pd.DataFrame]:
    """μ y Σ anuales desde retornos log mensuales (precios diarios → mensual)."""
    monthly = metrics.monthly_returns(prices)
    mu = monthly.mean() * config.MONTHS_PER_YEAR
    cov = monthly.cov(ddof=1) * config.MONTHS_PER_YEAR
    mu.name = "expected_return"
    return mu, cov


def estimate_monthly_inputs(
    prices: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.DataFrame]:
    """Retornos, μ, Σ y correlación mensuales."""
    monthly = metrics.monthly_returns(prices)
    mu = monthly.mean()
    mu.name = "expected_return_monthly"
    cov = monthly.cov(ddof=1)
    corr = monthly.corr()
    return monthly, mu, cov, corr


def build_standard_portfolios(
    prices: pd.DataFrame,
    benchmark_prices: pd.Series | None = None,
    risk_free_rate: float | None = None,
    capital: float | None = None,
    long_only: bool = True,
) -> dict[str, dict]:
    """Genera siempre los 3 portafolios estándar (mensual/anual)."""
    if prices is None or prices.empty:
        raise ValueError("No hay precios para construir portafolios.")

    tickers = validate_tickers(prices.columns.tolist())
    price_data = prices[tickers]
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate

    if benchmark_prices is not None:
        price_data, bench_aligned = _align_prices_with_benchmark(
            price_data,
            benchmark_prices,
        )
    else:
        bench_aligned = None

    monthly_rets, mu_m, cov_m, corr_m = estimate_monthly_inputs(price_data)
    mu_a = mu_m * config.MONTHS_PER_YEAR
    cov_a = cov_m * config.MONTHS_PER_YEAR

    bench_monthly = None
    if bench_aligned is not None:
        bench_monthly = metrics.monthly_returns(bench_aligned)

    weights_equal = equal_weights(tickers)
    weights_max_sharpe = maximum_sharpe_weights(
        expected_returns=mu_a,
        cov_matrix=cov_a,
        risk_free_rate=rf,
        long_only=long_only,
    )
    weights_min_var = minimum_variance_weights(
        cov_matrix=cov_a,
        long_only=long_only,
    )

    # Solo nombres compatibles (evita choque con caché vieja de Streamlit).
    common_kwargs = {
        "expected_returns": mu_a,
        "cov_matrix": cov_a,
        "asset_returns": monthly_rets,
        "benchmark_returns": bench_monthly,
        "risk_free_rate": rf,
        "capital": capital,
        "correlation": corr_m,
    }

    portfolios = {
        PORTFOLIO_EQUAL_WEIGHT: evaluate_portfolio(
            PORTFOLIO_EQUAL_WEIGHT,
            weights_equal,
            **common_kwargs,
        ),
        PORTFOLIO_MAX_SHARPE: evaluate_portfolio(
            PORTFOLIO_MAX_SHARPE,
            weights_max_sharpe,
            **common_kwargs,
        ),
        PORTFOLIO_MIN_VARIANCE: evaluate_portfolio(
            PORTFOLIO_MIN_VARIANCE,
            weights_min_var,
            **common_kwargs,
        ),
    }
    for portfolio in portfolios.values():
        portfolio["assets_covariance_matrix"] = cov_m
        portfolio["assets_covariance_matrix_annual"] = cov_a
        portfolio["assets_correlation_matrix"] = corr_m
    return portfolios


def _align_prices_with_benchmark(
    prices: pd.DataFrame,
    benchmark: pd.Series,
) -> tuple[pd.DataFrame, pd.Series]:
    """Alinea precios de activos con el benchmark por fechas comunes."""
    bench = benchmark.copy()
    bench.name = bench.name or "Benchmark"
    combined = prices.join(bench, how="inner").dropna()
    if combined.empty:
        raise ValueError("No hay fechas en común entre activos y benchmark.")
    return combined[prices.columns], combined[bench.name]


def portfolios_summary_table(portfolios: dict[str, dict]) -> pd.DataFrame:
    """Tabla resumen mensual + anual de los 3 portafolios."""
    rows: list[dict] = []
    for name, portfolio in portfolios.items():
        row = {
            "Portafolio": name,
            "Rendimiento (mensual)": portfolio.get("rendimiento_mensual"),
            "Rendimiento (anual)": portfolio.get(
                "rendimiento_anual",
                portfolio.get("rendimiento"),
            ),
            "Varianza (mensual)": portfolio.get("varianza_mensual"),
            "Varianza (anual)": portfolio.get(
                "varianza_anual",
                portfolio.get("varianza"),
            ),
            "Desviacion E. (mensual)": portfolio.get("desviacion_estandar_mensual"),
            "Desviacion E. (anual)": portfolio.get(
                "desviacion_estandar_anual",
                portfolio.get("desviacion_estandar"),
            ),
            "Beta": portfolio.get("beta"),
            "Sharpe (anual)": portfolio.get("sharpe"),
            "Treynor": portfolio.get("treynor"),
            "Jensen": portfolio.get("jensen"),
        }
        for ticker, weight in portfolio["weights"].items():
            row[f"Peso {ticker}"] = float(weight)
        rows.append(row)
    return pd.DataFrame(rows).set_index("Portafolio")


def get_portfolio_matrices(portfolio: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devuelve (covarianza, correlación) de los activos del portafolio."""
    return portfolio["covariance_matrix"], portfolio["correlation_matrix"]
