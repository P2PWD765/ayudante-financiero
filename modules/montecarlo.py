"""
Simulación Monte Carlo de portafolios.

Genera trayectorias de valor usando retornos log mensuales
multivariados N(μ, Σ) y pesos fijos del portafolio.

Incluye tres escenarios: Pesimista, Normal y Optimista
(ajustando media y volatilidad sobre la misma muestra aleatoria).
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import config
from modules.helpers import validate_tickers
from modules.portfolio import normalize_weights

SCENARIO_ORDER = ("Pesimista", "Normal", "Optimista")


def apply_scenario_inputs(
    expected_returns_monthly: pd.Series,
    cov_matrix_monthly: pd.DataFrame,
    scenario: str,
) -> tuple[pd.Series, pd.DataFrame, dict[str, float]]:
    """Ajusta μ y Σ según el escenario.

    Regla:
    - μ' = μ + k · σ_i  (σ_i = desviación mensual de cada activo)
    - Σ' = Σ · vol_scale²

    Args:
        expected_returns_monthly: Medias mensuales base.
        cov_matrix_monthly: Covarianza mensual base.
        scenario: Nombre en config.MONTE_CARLO_SCENARIOS.

    Returns:
        (mu_ajustada, cov_ajustada, params_del_escenario).
    """
    params = config.MONTE_CARLO_SCENARIOS.get(scenario)
    if params is None:
        raise ValueError(
            f"Escenario desconocido: {scenario}. "
            f"Usa: {', '.join(config.MONTE_CARLO_SCENARIOS)}"
        )

    k = float(params["mu_shift_sigma"])
    vol_scale = float(params["vol_scale"])
    if vol_scale <= 0:
        raise ValueError("vol_scale debe ser positivo.")

    mu = expected_returns_monthly.astype(float).copy()
    cov = cov_matrix_monthly.astype(float).copy()
    asset_vol = np.sqrt(np.clip(np.diag(cov.values), 0.0, None))
    mu_adj = mu + k * pd.Series(asset_vol, index=cov.index)
    cov_adj = cov * (vol_scale**2)
    return mu_adj, cov_adj, {"mu_shift_sigma": k, "vol_scale": vol_scale}


def simulate_portfolio_paths(
    expected_returns_monthly: pd.Series,
    cov_matrix_monthly: pd.DataFrame,
    weights: pd.Series,
    *,
    n_simulations: int | None = None,
    horizon_months: int | None = None,
    initial_value: float = 100_000.0,
    seed: int | None = None,
    z_shocks: np.ndarray | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Simula trayectorias de valor del portafolio (pesos fijos).

    Cada mes se muestrean retornos log de los activos ~ N(μ, Σ),
    se aplica el portafolio r_p = w'r y se acumula V_t = V_{t-1} * exp(r_p).

    Args:
        expected_returns_monthly: Media mensual por activo (μ).
        cov_matrix_monthly: Covarianza mensual (Σ).
        weights: Pesos del portafolio (suman 1).
        n_simulations: Número de trayectorias.
        horizon_months: Horizonte en meses.
        initial_value: Capital inicial.
        seed: Semilla RNG (reproducibilidad).
        z_shocks: Shocks N(0,1) opcionales (n_sim, horizon, n_assets).
            Si se pasan, se reutilizan (útil para comparar escenarios).
        scenario: Etiqueta opcional del escenario.

    Returns:
        Dict con paths, percentiles, valores finales y métricas de cola.
    """
    n_sim = int(n_simulations or config.MONTE_CARLO_SIMULATIONS)
    horizon = int(horizon_months or config.MONTE_CARLO_HORIZON_MONTHS)
    rng_seed = config.MONTE_CARLO_SEED if seed is None else seed

    if n_sim < 100:
        raise ValueError("Usa al menos 100 simulaciones.")
    if horizon < 1:
        raise ValueError("El horizonte debe ser al menos 1 mes.")
    if initial_value <= 0:
        raise ValueError("El capital inicial debe ser positivo.")

    w = normalize_weights(weights)
    tickers = validate_tickers(w.index.tolist())
    mu = expected_returns_monthly.reindex(tickers).astype(float)
    cov = cov_matrix_monthly.reindex(index=tickers, columns=tickers).astype(float)

    if mu.isna().any():
        missing = mu[mu.isna()].index.tolist()
        raise ValueError(f"Faltan medias mensuales para: {', '.join(missing)}")
    if cov.isna().any().any():
        raise ValueError("La matriz de covarianzas tiene valores faltantes.")

    cov_values = _as_psd(cov.values)
    chol = np.linalg.cholesky(cov_values)
    mu_values = mu.values
    w_values = w.reindex(tickers).values.astype(float)
    n_assets = len(tickers)

    if z_shocks is None:
        rng = np.random.default_rng(rng_seed)
        z = rng.standard_normal(size=(n_sim, horizon, n_assets))
    else:
        z = np.asarray(z_shocks, dtype=float)
        if z.shape != (n_sim, horizon, n_assets):
            raise ValueError(
                f"z_shocks debe tener forma {(n_sim, horizon, n_assets)}, "
                f"recibido {z.shape}."
            )

    asset_rets = mu_values + z @ chol.T
    port_rets = asset_rets @ w_values  # (n_sim, horizon)

    log_cum = np.cumsum(port_rets, axis=1)
    paths = np.empty((n_sim, horizon + 1), dtype=float)
    paths[:, 0] = initial_value
    paths[:, 1:] = initial_value * np.exp(log_cum)

    months = np.arange(horizon + 1)
    percentile_levels = (5, 25, 50, 75, 95)
    percentile_rows = {
        f"P{p}": np.percentile(paths, p, axis=0) for p in percentile_levels
    }
    percentiles = pd.DataFrame(percentile_rows, index=months)
    percentiles.index.name = "Mes"

    final_values = pd.Series(paths[:, -1], name="valor_final")
    final_returns = final_values / initial_value - 1.0
    loss_returns = -final_returns

    var_95 = float(np.percentile(loss_returns, 95))
    tail = loss_returns[loss_returns >= var_95]
    cvar_95 = float(tail.mean()) if len(tail) else var_95

    summary = {
        "n_simulations": n_sim,
        "horizon_months": horizon,
        "initial_value": float(initial_value),
        "seed": rng_seed,
        "scenario": scenario,
        "mean_final": float(final_values.mean()),
        "median_final": float(final_values.median()),
        "p5_final": float(final_values.quantile(0.05)),
        "p95_final": float(final_values.quantile(0.95)),
        "mean_return": float(final_returns.mean()),
        "median_return": float(final_returns.median()),
        "prob_loss": float((final_values < initial_value).mean()),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "var_95_money": var_95 * initial_value,
        "cvar_95_money": cvar_95 * initial_value,
    }

    return {
        "paths": paths,
        "months": months,
        "percentiles": percentiles,
        "final_values": final_values,
        "final_returns": final_returns,
        "summary": summary,
        "tickers": tickers,
        "weights": w.reindex(tickers),
        "scenario": scenario,
        "z_shocks": z,
    }


def simulate_scenarios_from_portfolio(
    portfolio: dict[str, Any],
    monthly_returns: pd.DataFrame,
    *,
    n_simulations: int | None = None,
    horizon_months: int | None = None,
    initial_value: float | None = None,
    seed: int | None = None,
    scenarios: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """Corre Pesimista / Normal / Optimista con los mismos shocks aleatorios.

    Args:
        portfolio: Portafolio evaluado (pesos, capital, nombre).
        monthly_returns: Retornos log mensuales por activo.
        n_simulations: Número de trayectorias.
        horizon_months: Horizonte en meses.
        initial_value: Capital inicial.
        seed: Semilla RNG.
        scenarios: Lista de escenarios (default: los 3 de config).

    Returns:
        Dict con:
        - scenarios: {nombre: resultado de simulate_portfolio_paths}
        - comparison: tabla resumen
        - portfolio_name, params por escenario
    """
    weights = portfolio["weights"]
    aligned = monthly_returns.reindex(columns=weights.index).dropna(how="any")
    if aligned.empty or len(aligned) < 3:
        raise ValueError(
            "No hay suficientes retornos mensuales alineados para Monte Carlo."
        )

    mu_base = aligned.mean()
    cov_base = aligned.cov(ddof=1)
    capital = initial_value
    if capital is None:
        capital = float(portfolio.get("capital") or 100_000.0)

    n_sim = int(n_simulations or config.MONTE_CARLO_SIMULATIONS)
    horizon = int(horizon_months or config.MONTE_CARLO_HORIZON_MONTHS)
    rng_seed = config.MONTE_CARLO_SEED if seed is None else seed
    names = scenarios or SCENARIO_ORDER

    tickers = validate_tickers(normalize_weights(weights).index.tolist())
    n_assets = len(tickers)
    rng = np.random.default_rng(rng_seed)
    z = rng.standard_normal(size=(n_sim, horizon, n_assets))

    results: dict[str, Any] = {}
    scenario_params: dict[str, dict[str, float]] = {}

    for name in names:
        mu_s, cov_s, params = apply_scenario_inputs(mu_base, cov_base, name)
        scenario_params[name] = params
        results[name] = simulate_portfolio_paths(
            mu_s,
            cov_s,
            weights,
            n_simulations=n_sim,
            horizon_months=horizon,
            initial_value=capital,
            seed=rng_seed,
            z_shocks=z,
            scenario=name,
        )

    comparison = scenarios_comparison_table(results)
    return {
        "scenarios": results,
        "comparison": comparison,
        "scenario_params": scenario_params,
        "portfolio_name": portfolio.get("name", "Portafolio"),
        "n_simulations": n_sim,
        "horizon_months": horizon,
        "initial_value": float(capital),
        "seed": rng_seed,
    }


def simulate_from_portfolio(
    portfolio: dict[str, Any],
    monthly_returns: pd.DataFrame,
    *,
    n_simulations: int | None = None,
    horizon_months: int | None = None,
    initial_value: float | None = None,
    seed: int | None = None,
    scenario: str = "Normal",
) -> dict[str, Any]:
    """Simula un solo escenario (compatibilidad). Preferir simulate_scenarios_*.

    Args:
        portfolio: Dict de evaluate_portfolio / build_standard_portfolios.
        monthly_returns: DataFrame de retornos log mensuales por activo.
        n_simulations: Número de trayectorias.
        horizon_months: Horizonte en meses.
        initial_value: Capital (default: capital del portafolio o config).
        seed: Semilla RNG.
        scenario: Escenario a aplicar.

    Returns:
        Resultado de simulate_portfolio_paths.
    """
    bundle = simulate_scenarios_from_portfolio(
        portfolio,
        monthly_returns,
        n_simulations=n_simulations,
        horizon_months=horizon_months,
        initial_value=initial_value,
        seed=seed,
        scenarios=(scenario,),
    )
    result = bundle["scenarios"][scenario]
    result["portfolio_name"] = bundle["portfolio_name"]
    return result


def scenarios_comparison_table(scenario_results: dict[str, dict[str, Any]]) -> pd.DataFrame:
    """Tabla comparativa de métricas clave por escenario."""
    rows: list[dict[str, Any]] = []
    for name in SCENARIO_ORDER:
        if name not in scenario_results:
            continue
        s = scenario_results[name]["summary"]
        rows.append(
            {
                "Escenario": name,
                "Valor medio final": s["mean_final"],
                "Mediana final": s["median_final"],
                "P5 final": s["p5_final"],
                "P95 final": s["p95_final"],
                "Retorno medio": s["mean_return"],
                "Prob. pérdida": s["prob_loss"],
                "VaR 95% (MC)": s["var_95"],
                "CVaR 95% (MC)": s["cvar_95"],
                "VaR 95% ($)": s["var_95_money"],
                "CVaR 95% ($)": s["cvar_95_money"],
            }
        )
    return pd.DataFrame(rows).set_index("Escenario")


def _as_psd(matrix: np.ndarray, epsilon: float = 1e-10) -> np.ndarray:
    """Proyecta una matriz a semidefinida positiva (para Cholesky)."""
    sym = 0.5 * (matrix + matrix.T)
    eigvals, eigvecs = np.linalg.eigh(sym)
    eigvals = np.clip(eigvals, epsilon, None)
    return eigvecs @ np.diag(eigvals) @ eigvecs.T
