"""
Optimización de portafolios (Markowitz).

Incluye:
- Portafolio de mínima varianza.
- Portafolio de máximo Sharpe.
- Frontera eficiente.
- Capital Allocation Line (CAL).

Restricción por defecto: long-only (pesos >= 0) y suma de pesos = 1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import cvxpy as cp

import config


def minimum_variance_weights(
    cov_matrix: pd.DataFrame,
    long_only: bool = True,
) -> pd.Series:
    """Calcula pesos del portafolio de mínima varianza.

    Minimiza w' Σ w sujeto a sum(w) = 1 (y w >= 0 si long_only).

    Args:
        cov_matrix: Matriz de covarianzas (misma frecuencia que se usará).
        long_only: Si True, no permite ventas en corto.

    Returns:
        Serie de pesos indexada por ticker.

    Raises:
        ValueError: Si la optimización no converge.
    """
    tickers = list(cov_matrix.columns)
    n = len(tickers)
    if n == 0:
        raise ValueError("La matriz de covarianzas está vacía.")
    if n == 1:
        return pd.Series([1.0], index=tickers, name="weight")

    sigma = _as_psd(cov_matrix.values)
    w = cp.Variable(n)
    objective = cp.Minimize(cp.quad_form(w, sigma))
    constraints = [cp.sum(w) == 1]
    if long_only:
        constraints.append(w >= 0)

    problem = cp.Problem(objective, constraints)
    _solve(problem, kind="qp")

    if w.value is None:
        raise ValueError(
            "No se pudo resolver el portafolio de mínima varianza. "
            f"Estado CVXPY: {problem.status}"
        )

    weights = _normalize_weights(np.asarray(w.value).ravel(), tickers)
    return weights


def maximum_sharpe_weights(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    risk_free_rate: float | None = None,
    long_only: bool = True,
) -> pd.Series:
    """Calcula pesos del portafolio de máximo Sharpe.

    Maximiza (μ - rf)' w / sqrt(w' Σ w) con sum(w) = 1
    (y w >= 0 si long_only).

    Reformulación convexa:
    maximizar (μ - rf)' y  s.t.  y' Σ y <= 1, y >= 0;
    luego normalizar para que los pesos sumen 1.

    Args:
        expected_returns: Retornos esperados por activo (misma freq. que rf).
        cov_matrix: Matriz de covarianzas alineada con expected_returns.
        risk_free_rate: Tasa libre de riesgo en la misma frecuencia.
        long_only: Si True, no permite ventas en corto.

    Returns:
        Serie de pesos indexada por ticker.

    Raises:
        ValueError: Si no hay exceso de retorno positivo o no converge.
    """
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    tickers = list(expected_returns.index)
    n = len(tickers)
    if n == 0:
        raise ValueError("No hay retornos esperados para optimizar.")
    if n == 1:
        return pd.Series([1.0], index=tickers, name="weight")

    mu = expected_returns.reindex(tickers).astype(float).values
    sigma = _as_psd(cov_matrix.reindex(index=tickers, columns=tickers).values)
    excess = mu - rf

    if np.all(excess <= 0):
        raise ValueError(
            "No se puede maximizar Sharpe: todos los excesos de retorno "
            "(μ - rf) son <= 0 con la tasa libre de riesgo actual."
        )

    y = cp.Variable(n)
    objective = cp.Maximize(excess @ y)
    constraints = [cp.quad_form(y, sigma) <= 1]
    if long_only:
        constraints.append(y >= 0)

    problem = cp.Problem(objective, constraints)
    _solve(problem, kind="qcqp")

    if y.value is None:
        raise ValueError(
            "No se pudo resolver el portafolio de máximo Sharpe. "
            f"Estado CVXPY: {problem.status}"
        )

    raw = np.asarray(y.value).ravel()
    if np.isclose(raw.sum(), 0):
        raise ValueError("La optimización de máximo Sharpe devolvió pesos nulos.")

    weights = _normalize_weights(raw, tickers)
    return weights


def target_return_weights(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    target_return: float,
    long_only: bool = True,
) -> pd.Series:
    """Pesos de mínima varianza sujetos a un retorno objetivo.

    Minimiza w' Σ w s.t. w' μ = target_return y sum(w) = 1.

    Args:
        expected_returns: Retornos esperados por activo.
        cov_matrix: Matriz de covarianzas.
        target_return: Retorno objetivo (misma frecuencia que μ).
        long_only: Si True, w >= 0.

    Returns:
        Serie de pesos.
    """
    tickers = list(expected_returns.index)
    n = len(tickers)
    if n == 0:
        raise ValueError("No hay retornos esperados para optimizar.")
    if n == 1:
        return pd.Series([1.0], index=tickers, name="weight")

    mu = expected_returns.reindex(tickers).astype(float).values
    sigma = _as_psd(cov_matrix.reindex(index=tickers, columns=tickers).values)

    w = cp.Variable(n)
    objective = cp.Minimize(cp.quad_form(w, sigma))
    constraints = [
        cp.sum(w) == 1,
        mu @ w == target_return,
    ]
    if long_only:
        constraints.append(w >= 0)

    problem = cp.Problem(objective, constraints)
    _solve(problem, kind="qp")

    if w.value is None:
        raise ValueError(
            "No se pudo alcanzar el retorno objetivo en la frontera. "
            f"Estado CVXPY: {problem.status}"
        )
    return _normalize_weights(np.asarray(w.value).ravel(), tickers)


def efficient_frontier(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    n_points: int | None = None,
    long_only: bool = True,
) -> pd.DataFrame:
    """Calcula la frontera eficiente de Markowitz.

    Para una grilla de retornos objetivo entre el min-var y el máximo μ
    individual factible, minimiza la varianza.

    Args:
        expected_returns: μ por activo.
        cov_matrix: Σ de activos.
        n_points: Cantidad de puntos en la frontera.
        long_only: Pesos >= 0.

    Returns:
        DataFrame con columnas: volatility, expected_return, sharpe, y pesos.
    """
    n_points = n_points or config.EFFICIENT_FRONTIER_POINTS
    tickers = list(expected_returns.index)
    mu = expected_returns.reindex(tickers).astype(float)
    cov = cov_matrix.reindex(index=tickers, columns=tickers)

    w_min = minimum_variance_weights(cov, long_only=long_only)
    ret_min = float(w_min @ mu)
    ret_max = float(mu.max())

    if ret_max <= ret_min:
        targets = np.array([ret_min])
    else:
        targets = np.linspace(ret_min, ret_max, n_points)

    rows: list[dict] = []
    for target in targets:
        try:
            weights = target_return_weights(
                expected_returns=mu,
                cov_matrix=cov,
                target_return=float(target),
                long_only=long_only,
            )
        except ValueError:
            continue

        vol = float(np.sqrt(weights.values @ cov.values @ weights.values))
        ret = float(weights @ mu)
        sharpe = (
            float((ret - config.RISK_FREE_RATE) / vol) if vol > 0 else float("nan")
        )
        row = {
            "volatility": vol,
            "expected_return": ret,
            "sharpe": sharpe,
        }
        for ticker, weight in weights.items():
            row[f"weight_{ticker}"] = float(weight)
        rows.append(row)

    if not rows:
        raise ValueError("No se pudo construir la frontera eficiente.")

    frontier = pd.DataFrame(rows).sort_values("volatility").reset_index(drop=True)
    return frontier


def capital_allocation_line(
    tangency_return: float,
    tangency_volatility: float,
    risk_free_rate: float | None = None,
    n_points: int | None = None,
    max_risky_weight: float | None = None,
) -> pd.DataFrame:
    """Calcula la Capital Allocation Line (CAL).

    Une el activo libre de riesgo (0, Rf) con el portafolio tangencial
    (máximo Sharpe) y puede extenderse más allá:

        R(y) = Rf + y * (R_t - Rf)
        σ(y) = y * σ_t

    donde y es la proporción invertida en el portafolio riesgoso.

    Args:
        tangency_return: Retorno esperado del portafolio tangencial.
        tangency_volatility: Volatilidad del portafolio tangencial.
        risk_free_rate: Rf anual.
        n_points: Cantidad de puntos de la línea.
        max_risky_weight: Máximo y (1.0 = 100% en tangencial).

    Returns:
        DataFrame con columns: risky_weight, volatility, expected_return.
    """
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    n_points = n_points or config.CAL_POINTS
    max_y = (
        config.CAL_MAX_RISKY_WEIGHT
        if max_risky_weight is None
        else max_risky_weight
    )

    if tangency_volatility <= 0:
        raise ValueError("La volatilidad del tangencial debe ser > 0.")

    ys = np.linspace(0.0, max_y, n_points)
    rows = []
    for y in ys:
        rows.append(
            {
                "risky_weight": float(y),
                "volatility": float(y * tangency_volatility),
                "expected_return": float(rf + y * (tangency_return - rf)),
            }
        )
    return pd.DataFrame(rows)


def portfolio_performance(
    weights: pd.Series,
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    risk_free_rate: float | None = None,
) -> dict[str, float]:
    """Calcula retorno, volatilidad y Sharpe de un vector de pesos.

    Args:
        weights: Pesos del portafolio.
        expected_returns: μ por activo.
        cov_matrix: Σ de activos.
        risk_free_rate: Rf.

    Returns:
        Dict con expected_return, volatility, variance, sharpe.
    """
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    tickers = list(weights.index)
    w = weights.reindex(tickers).astype(float).values
    mu = expected_returns.reindex(tickers).astype(float).values
    cov = cov_matrix.reindex(index=tickers, columns=tickers).values

    ret = float(w @ mu)
    var = float(w @ cov @ w)
    vol = float(np.sqrt(var))
    sharpe = float((ret - rf) / vol) if vol > 0 else float("nan")
    return {
        "expected_return": ret,
        "variance": var,
        "volatility": vol,
        "sharpe": sharpe,
    }


def run_markowitz_analysis(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    risk_free_rate: float | None = None,
    n_frontier_points: int | None = None,
    long_only: bool | None = None,
) -> dict:
    """Ejecuta el análisis Markowitz completo de la Fase 4.

    Args:
        expected_returns: μ anual por activo.
        cov_matrix: Σ anual.
        risk_free_rate: Rf anual.
        n_frontier_points: Puntos de la frontera.
        long_only: Si None, usa config.LONG_ONLY.

    Returns:
        Diccionario con:
        - min_variance / max_sharpe (pesos + performance)
        - frontier (DataFrame)
        - cal (DataFrame)
        - assets (riesgo/retorno individuales)
    """
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    long_only = config.LONG_ONLY if long_only is None else long_only

    tickers = list(expected_returns.index)
    mu = expected_returns.reindex(tickers).astype(float)
    cov = cov_matrix.reindex(index=tickers, columns=tickers)

    w_min = minimum_variance_weights(cov, long_only=long_only)
    w_max = maximum_sharpe_weights(mu, cov, risk_free_rate=rf, long_only=long_only)

    perf_min = portfolio_performance(w_min, mu, cov, risk_free_rate=rf)
    perf_max = portfolio_performance(w_max, mu, cov, risk_free_rate=rf)

    frontier = efficient_frontier(
        expected_returns=mu,
        cov_matrix=cov,
        n_points=n_frontier_points,
        long_only=long_only,
    )
    cal = capital_allocation_line(
        tangency_return=perf_max["expected_return"],
        tangency_volatility=perf_max["volatility"],
        risk_free_rate=rf,
    )

    assets = pd.DataFrame(
        {
            "expected_return": mu,
            "volatility": np.sqrt(np.diag(cov.values)),
        },
        index=tickers,
    )

    return {
        "risk_free_rate": rf,
        "min_variance": {"weights": w_min, **perf_min},
        "max_sharpe": {"weights": w_max, **perf_max},
        "frontier": frontier,
        "cal": cal,
        "assets": assets,
    }


def _normalize_weights(raw: np.ndarray, tickers: list[str]) -> pd.Series:
    """Normaliza pesos para que sumen 1 y limpia residuos numéricos."""
    cleaned = np.clip(raw, 0, None)
    total = cleaned.sum()
    if total <= 0:
        raise ValueError("La suma de pesos es cero; no se pueden normalizar.")
    cleaned = cleaned / total
    cleaned[cleaned < 1e-10] = 0.0
    cleaned = cleaned / cleaned.sum()
    return pd.Series(cleaned, index=tickers, name="weight")


def _as_psd(matrix: np.ndarray) -> np.ndarray:
    """Asegura una matriz simétrica semidefinida positiva (estabilidad numérica)."""
    sym = 0.5 * (matrix + matrix.T)
    eigvals = np.linalg.eigvalsh(sym)
    min_eig = float(np.min(eigvals)) if len(eigvals) else 0.0
    if min_eig < 1e-10:
        sym = sym + (abs(min_eig) + 1e-8) * np.eye(sym.shape[0])
    return sym


def _solve(problem: cp.Problem, kind: str = "qp") -> None:
    """Resuelve un problema CVXPY con un solver compatible.

    Args:
        problem: Problema CVXPY.
        kind: 'qp' para mínima varianza; 'qcqp' para máximo Sharpe.
    """
    installed = set(cp.installed_solvers())
    if kind == "qp":
        candidates = ("OSQP", "ECOS", "SCS", "CLARABEL")
    else:
        candidates = ("SCS", "ECOS", "CLARABEL")

    last_error: Exception | None = None
    for name in candidates:
        if name not in installed:
            continue
        try:
            problem.solve(solver=getattr(cp, name), warm_start=False)
            if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            continue

    try:
        problem.solve()
        if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            return
    except Exception as exc:  # noqa: BLE001
        last_error = exc

    detail = f" Último error: {last_error}" if last_error else ""
    raise ValueError(
        f"No hay solver compatible o la optimización falló ({kind}).{detail}"
    )
