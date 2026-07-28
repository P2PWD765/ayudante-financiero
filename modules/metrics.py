"""
Cálculo de métricas financieras.

Todas las métricas siguen las fórmulas del proyecto:
- Rendimientos logarítmicos: R = ln(P_t / P_{t-1})
- Varianza / desviación muestral (n - 1)
- VaR paramétrico
- Beta, Alpha de Jensen y Sharpe según CAPM

Las páginas de Streamlit no deben calcular nada aquí:
solo deben llamar a estas funciones.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import config


# ---------------------------------------------------------------------------
# Rendimientos logarítmicos
# ---------------------------------------------------------------------------

def log_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Calcula rendimientos logarítmicos: ln(P_t / P_{t-1}).

    Args:
        prices: Serie o DataFrame de precios.

    Returns:
        Rendimientos logarítmicos, sin la primera fila NaN.
    """
    returns = np.log(prices / prices.shift(1))
    return returns.dropna(how="all")


def daily_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimientos diarios logarítmicos.

    Args:
        prices: Precios diarios.

    Returns:
        R_diario = ln(P_t / P_{t-1}).
    """
    return log_returns(prices)


def weekly_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimientos semanales logarítmicos (cierre de cada semana).

    Args:
        prices: Precios diarios.

    Returns:
        R_semanal = ln(P_semana / P_semana_anterior).
    """
    weekly_prices = prices.resample("W").last().dropna(how="all")
    return log_returns(weekly_prices)


def monthly_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimientos mensuales logarítmicos (cierre de cada mes).

    Args:
        prices: Precios diarios.

    Returns:
        R_mensual = ln(P_mes / P_mes_anterior).
    """
    monthly_prices = prices.resample("ME").last().dropna(how="all")
    return log_returns(monthly_prices)


def cumulative_log_returns(
    prices: pd.DataFrame | pd.Series,
) -> pd.DataFrame | pd.Series:
    """Rendimiento acumulado logarítmico: suma de r_i.

    Args:
        prices: Serie o DataFrame de precios.

    Returns:
        Suma acumulada de rendimientos logarítmicos.
    """
    return log_returns(prices).cumsum()


def cumulative_returns(prices: pd.DataFrame | pd.Series) -> pd.DataFrame | pd.Series:
    """Rendimiento acumulado real: exp(sum r_i) - 1.

    Args:
        prices: Serie o DataFrame de precios.

    Returns:
        Crecimiento aritmético desde el capital inicial (decimal).
    """
    return np.exp(cumulative_log_returns(prices)) - 1.0


# ---------------------------------------------------------------------------
# Riesgo básico
# ---------------------------------------------------------------------------

def variance(
    returns: pd.DataFrame | pd.Series,
    annualize: bool = False,
    periods_per_year: int | None = None,
) -> pd.Series | float:
    """Varianza muestral: sum((R_i - mu)^2) / (n - 1).

    Args:
        returns: Rendimientos logarítmicos.
        annualize: Si True, multiplica por periodos por año.
        periods_per_year: Factor de anualización (default: días hábiles).

    Returns:
        Varianza por activo o escalar.
    """
    # ddof=1 => divisor (n - 1), igual que la fórmula del proyecto.
    var = returns.var(ddof=1)
    if annualize:
        periods = periods_per_year or config.TRADING_DAYS_PER_YEAR
        var = var * periods
    return var


def standard_deviation(
    returns: pd.DataFrame | pd.Series,
    annualize: bool = False,
    periods_per_year: int | None = None,
) -> pd.Series | float:
    """Desviación estándar muestral (volatilidad).

    Args:
        returns: Rendimientos logarítmicos.
        annualize: Si True, multiplica por sqrt(periodos por año).
        periods_per_year: Factor de anualización.

    Returns:
        Desviación estándar por activo o escalar.
    """
    std = returns.std(ddof=1)
    if annualize:
        periods = periods_per_year or config.TRADING_DAYS_PER_YEAR
        std = std * np.sqrt(periods)
    return std


def volatility_weekly(
    prices: pd.DataFrame | pd.Series,
    annualize: bool | None = None,
) -> pd.Series | float:
    """Volatilidad con rendimientos semanales logarítmicos.

    Args:
        prices: Precios diarios.
        annualize: Si None, usa config.ANNUALIZE_VOLATILITY.

    Returns:
        Volatilidad semanal (anualizada o no).
    """
    if annualize is None:
        annualize = config.ANNUALIZE_VOLATILITY
    returns = weekly_returns(prices)
    return standard_deviation(
        returns,
        annualize=annualize,
        periods_per_year=config.WEEKS_PER_YEAR,
    )


def volatility_monthly(
    prices: pd.DataFrame | pd.Series,
    annualize: bool | None = None,
) -> pd.Series | float:
    """Volatilidad con rendimientos mensuales logarítmicos.

    Args:
        prices: Precios diarios.
        annualize: Si None, usa config.ANNUALIZE_VOLATILITY.

    Returns:
        Volatilidad mensual (anualizada o no).
    """
    if annualize is None:
        annualize = config.ANNUALIZE_VOLATILITY
    returns = monthly_returns(prices)
    return standard_deviation(
        returns,
        annualize=annualize,
        periods_per_year=config.MONTHS_PER_YEAR,
    )


# ---------------------------------------------------------------------------
# Relación entre activos y mercado
# ---------------------------------------------------------------------------

def covariance(x: pd.Series, y: pd.Series) -> float:
    """Covarianza muestral entre dos series: Cov(X, Y).

    Args:
        x: Rendimientos del activo X.
        y: Rendimientos del activo Y (o mercado).

    Returns:
        Covarianza con divisor (n - 1).
    """
    aligned = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    return float(aligned["x"].cov(aligned["y"], ddof=1))


def correlation(x: pd.Series, y: pd.Series) -> float:
    """Correlación: Cov(X, Y) / (sigma_X * sigma_Y).

    Args:
        x: Rendimientos X.
        y: Rendimientos Y.

    Returns:
        Correlación entre -1 y 1.
    """
    aligned = pd.concat([x.rename("x"), y.rename("y")], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")

    cov = aligned["x"].cov(aligned["y"], ddof=1)
    std_x = aligned["x"].std(ddof=1)
    std_y = aligned["y"].std(ddof=1)
    if std_x == 0 or std_y == 0 or pd.isna(std_x) or pd.isna(std_y):
        return float("nan")
    return float(cov / (std_x * std_y))


def beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Beta: Cov(R_activo, R_mercado) / Var(R_mercado).

    Args:
        asset_returns: Rendimientos logarítmicos del activo.
        benchmark_returns: Rendimientos logarítmicos del mercado.

    Returns:
        Beta del activo.
    """
    aligned = pd.concat(
        [asset_returns.rename("asset"), benchmark_returns.rename("market")],
        axis=1,
    ).dropna()

    if len(aligned) < 2:
        return float("nan")

    cov = aligned["asset"].cov(aligned["market"], ddof=1)
    market_var = aligned["market"].var(ddof=1)
    if market_var == 0 or pd.isna(market_var):
        return float("nan")
    return float(cov / market_var)


def jensen_alpha(
    asset_returns: pd.Series,
    benchmark_returns: pd.Series,
    risk_free_rate: float | None = None,
    periods_per_year: int | None = None,
) -> float:
    """Alpha de Jensen: Rp - [Rf + Beta * (Rm - Rf)].

    Se calcula en la frecuencia de los rendimientos y se anualiza.

    Args:
        asset_returns: Rendimientos logarítmicos del activo.
        benchmark_returns: Rendimientos logarítmicos del mercado.
        risk_free_rate: Tasa libre de riesgo anual.
        periods_per_year: Periodos por año (252 diario, 12 mensual, etc.).

    Returns:
        Alpha anualizado en forma decimal.
    """
    rf_annual = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    periods = periods_per_year or config.TRADING_DAYS_PER_YEAR

    aligned = pd.concat(
        [asset_returns.rename("asset"), benchmark_returns.rename("market")],
        axis=1,
    ).dropna()
    if len(aligned) < 2:
        return float("nan")

    asset_beta = beta(aligned["asset"], aligned["market"])
    if pd.isna(asset_beta):
        return float("nan")

    rf_period = rf_annual / periods
    rp = float(aligned["asset"].mean())
    rm = float(aligned["market"].mean())
    alpha_period = rp - (rf_period + asset_beta * (rm - rf_period))
    return float(alpha_period * periods)


def sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float | None = None,
    periods_per_year: int | None = None,
) -> float:
    """Sharpe Ratio: (Rp - Rf) / sigma_p, anualizado.

    Args:
        returns: Rendimientos logarítmicos.
        risk_free_rate: Tasa libre de riesgo anual.
        periods_per_year: Periodos por año para anualizar.

    Returns:
        Sharpe anualizado.
    """
    rf_annual = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    periods = periods_per_year or config.TRADING_DAYS_PER_YEAR

    clean = returns.dropna()
    if clean.empty:
        return float("nan")

    rf_period = rf_annual / periods
    rp = float(clean.mean())
    sigma = float(clean.std(ddof=1))
    if sigma == 0 or pd.isna(sigma):
        return float("nan")

    # Equivalente a anualizar media y sigma por separado:
    # ((rp - rf_period) * periods) / (sigma * sqrt(periods))
    return float(((rp - rf_period) / sigma) * np.sqrt(periods))


def treynor_ratio(
    expected_return: float,
    beta_value: float,
    risk_free_rate: float | None = None,
) -> float:
    """Treynor Ratio: (Rp - Rf) / Beta.

    Args:
        expected_return: Retorno del activo/portafolio (anual).
        beta_value: Beta respecto al mercado.
        risk_free_rate: Tasa libre de riesgo anual.

    Returns:
        Treynor Ratio. NaN si Beta es 0 o inválido.
    """
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    if beta_value == 0 or pd.isna(beta_value):
        return float("nan")
    return float((expected_return - rf) / beta_value)


# ---------------------------------------------------------------------------
# VaR paramétrico y matrices
# ---------------------------------------------------------------------------

def _z_score(confidence: float) -> float:
    """Valor Z de la normal estándar para un nivel de confianza.

    Args:
        confidence: Ej. 0.95 -> Z ≈ 1.64485.

    Returns:
        Cuantil normal.
    """
    return float(stats.norm.ppf(confidence))


def value_at_risk(
    returns: pd.Series,
    confidence: float = 0.95,
    capital: float = 1.0,
) -> float:
    """VaR paramétrico: Capital * (Z * sigma - mu).

    Asume distribución normal de los rendimientos.

    Args:
        returns: Rendimientos logarítmicos del periodo.
        confidence: Nivel de confianza (0.95 o 0.99).
        capital: Capital expuesto (1.0 = VaR en unidades de retorno).

    Returns:
        VaR paramétrico (pérdida esperada máxima bajo el modelo).
    """
    clean = returns.dropna()
    if clean.empty:
        return float("nan")

    mu = float(clean.mean())
    sigma = float(clean.std(ddof=1))
    if pd.isna(sigma):
        return float("nan")

    z = _z_score(confidence)
    return float(capital * (z * sigma - mu))


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Matriz de correlaciones entre activos.

    Args:
        returns: DataFrame de rendimientos logarítmicos.

    Returns:
        Matriz de correlación (ddof implícito de pandas).
    """
    return returns.corr()


def covariance_matrix(
    returns: pd.DataFrame,
    annualize: bool = False,
    periods_per_year: int | None = None,
) -> pd.DataFrame:
    """Matriz de covarianzas muestrales entre activos.

    Args:
        returns: DataFrame de rendimientos logarítmicos.
        annualize: Si True, anualiza la matriz.
        periods_per_year: Factor de anualización.

    Returns:
        Matriz de covarianza.
    """
    cov = returns.cov(ddof=1)
    if annualize:
        periods = periods_per_year or config.TRADING_DAYS_PER_YEAR
        cov = cov * periods
    return cov


# ---------------------------------------------------------------------------
# Resumen por activo
# ---------------------------------------------------------------------------

def summary_metrics(
    prices: pd.DataFrame,
    benchmark_prices: pd.Series | None = None,
    risk_free_rate: float | None = None,
) -> pd.DataFrame:
    """Resumen de métricas por activo (solo mensual y anual).

    Los precios de entrada son diarios; los cálculos usan retornos
    logarítmicos mensuales y su anualización (x12 / √12).

    Args:
        prices: Precios históricos diarios.
        benchmark_prices: Precios del benchmark (para Alpha/Beta).
        risk_free_rate: Tasa libre de riesgo anual.

    Returns:
        DataFrame con métricas mensuales y anuales por ticker.
    """
    monthly = monthly_returns(prices)

    bench_monthly = None
    if benchmark_prices is not None:
        bench_monthly = monthly_returns(benchmark_prices)

    rows: list[dict] = []
    for ticker in prices.columns:
        asset_monthly = monthly[ticker].dropna()
        mu_m = float(asset_monthly.mean())
        var_m = float(asset_monthly.var(ddof=1))
        std_m = float(asset_monthly.std(ddof=1))

        row: dict = {
            "Ticker": ticker,
            "Rendimiento acumulado": float(
                cumulative_returns(prices[ticker]).iloc[-1]
            ),
            "Rendimiento (mensual)": mu_m,
            "Rendimiento (anual)": mu_m * config.MONTHS_PER_YEAR,
            "Varianza (mensual)": var_m,
            "Varianza (anual)": var_m * config.MONTHS_PER_YEAR,
            "Desviacion E. (mensual)": std_m,
            "Desviacion E. (anual)": std_m * np.sqrt(config.MONTHS_PER_YEAR),
            "Sharpe (anual)": sharpe_ratio(
                asset_monthly,
                risk_free_rate=risk_free_rate,
                periods_per_year=config.MONTHS_PER_YEAR,
            ),
            "VaR 95% (mensual)": value_at_risk(
                asset_monthly,
                confidence=0.95,
                capital=1.0,
            ),
        }

        if bench_monthly is not None:
            row["Beta"] = beta(asset_monthly, bench_monthly)
            row["Alpha de Jensen"] = jensen_alpha(
                asset_monthly,
                bench_monthly,
                risk_free_rate=risk_free_rate,
                periods_per_year=config.MONTHS_PER_YEAR,
            )

        rows.append(row)

    return pd.DataFrame(rows).set_index("Ticker")
