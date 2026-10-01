"""
Modelo Black-Litterman.

Combina el prior de equilibrio de mercado (π) con views del usuario
para obtener retornos esperados posteriores μ_BL y pesos óptimos.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np
import pandas as pd

import config
from modules import optimization
from modules.helpers import validate_tickers
from modules.portfolio import equal_weights, normalize_weights


ViewType = Literal["absoluta", "relativa"]


def market_weights_from_caps(
    tickers: list[str],
    fundamentals: pd.DataFrame | None,
) -> pd.Series:
    """Pesos de mercado por capitalización; si faltan, equiponderado.

    Args:
        tickers: Activos del análisis.
        fundamentals: Tabla con columna 'Market Cap' (opcional).

    Returns:
        Serie de pesos que suman 1.
    """
    symbols = validate_tickers(tickers)
    if fundamentals is None or "Market Cap" not in fundamentals.columns:
        return equal_weights(symbols)

    caps = pd.to_numeric(
        fundamentals.reindex(symbols)["Market Cap"],
        errors="coerce",
    )
    if caps.isna().all() or float(caps.fillna(0).sum()) <= 0:
        return equal_weights(symbols)

    caps = caps.fillna(0.0).clip(lower=0.0)
    if float(caps.sum()) <= 0:
        return equal_weights(symbols)
    return normalize_weights(caps)


def equilibrium_returns(
    cov_matrix: pd.DataFrame,
    market_weights: pd.Series,
    *,
    delta: float | None = None,
) -> pd.Series:
    """Retornos de equilibrio: π = δ Σ w_mkt.

    Args:
        cov_matrix: Covarianza (misma frecuencia que los retornos deseados).
        market_weights: Pesos de mercado.
        delta: Aversión al riesgo implícita.

    Returns:
        Serie π indexada por ticker.
    """
    delta_val = float(config.BL_DELTA if delta is None else delta)
    tickers = list(cov_matrix.columns)
    w = normalize_weights(market_weights).reindex(tickers).fillna(0.0)
    cov = cov_matrix.reindex(index=tickers, columns=tickers).astype(float)
    pi = delta_val * cov.values @ w.values
    return pd.Series(pi, index=tickers, name="equilibrium_return")


def build_views_matrices(
    tickers: list[str],
    views: list[dict[str, Any]],
) -> tuple[pd.DataFrame, pd.Series]:
    """Construye matrices P y Q a partir de views del usuario.

    Cada view es un dict:
    - type: 'absoluta' | 'relativa'
    - asset: ticker principal
    - other: ticker de comparación (solo relativa)
    - return: retorno esperado anual (absoluto) o diferencial anual (relativo)
    - confidence: 0–1 (se usa al armar Ω; no entra en P/Q)

    Args:
        tickers: Universo de activos.
        views: Lista de views válidas.

    Returns:
        (P, Q) con P de forma (k, n) y Q de forma (k,).

    Raises:
        ValueError: Si no hay views válidas.
    """
    symbols = validate_tickers(tickers)
    index_map = {t: i for i, t in enumerate(symbols)}
    rows: list[np.ndarray] = []
    q_vals: list[float] = []

    for i, view in enumerate(views, start=1):
        vtype = str(view.get("type", "absoluta")).strip().lower()
        asset = str(view.get("asset", "")).strip().upper()
        ret = float(view.get("return"))
        if asset not in index_map:
            raise ValueError(f"View {i}: ticker '{asset}' no está en el portafolio.")

        row = np.zeros(len(symbols), dtype=float)
        if vtype.startswith("abs"):
            row[index_map[asset]] = 1.0
            q_vals.append(ret)
        elif vtype.startswith("rel"):
            other = str(view.get("other", "")).strip().upper()
            if other not in index_map:
                raise ValueError(
                    f"View {i}: ticker de comparación '{other}' no está en el portafolio."
                )
            if other == asset:
                raise ValueError(f"View {i}: los dos tickers de una view relativa deben diferir.")
            # asset − other = return  (ej. MSFT supera a GOOGL en +2%)
            row[index_map[asset]] = 1.0
            row[index_map[other]] = -1.0
            q_vals.append(ret)
        else:
            raise ValueError(f"View {i}: tipo '{vtype}' no soportado (usa absoluta/relativa).")

        rows.append(row)

    if not rows:
        raise ValueError("Debes indicar al menos una view válida.")

    p = pd.DataFrame(rows, columns=symbols)
    q = pd.Series(q_vals, name="view_return")
    return p, q


def view_uncertainty(
    p: pd.DataFrame,
    cov_matrix: pd.DataFrame,
    views: list[dict[str, Any]],
    *,
    tau: float | None = None,
) -> pd.DataFrame:
    """Matriz Ω diagonal: incertidumbre de cada view.

    Ω_ii = (1 / confianza_i) * tau * (P Σ P')_ii
    confianza cercana a 1 → Ω pequeña → la view pesa más.

    Args:
        p: Matriz de views.
        cov_matrix: Covarianza anual.
        views: Views originales (para confianza).
        tau: Escalado de incertidumbre del prior.

    Returns:
        DataFrame Ω (k x k).
    """
    tau_val = float(config.BL_TAU if tau is None else tau)
    tickers = list(p.columns)
    cov = cov_matrix.reindex(index=tickers, columns=tickers).astype(float)
    p_sigma_p = p.values @ cov.values @ p.values.T
    diag = np.diag(p_sigma_p).astype(float)

    omega_diag = []
    for i, view in enumerate(views):
        conf = float(view.get("confidence", config.BL_DEFAULT_CONFIDENCE))
        conf = float(np.clip(conf, 0.05, 1.0))
        base = max(float(diag[i]), 1e-12)
        omega_diag.append((1.0 / conf) * tau_val * base)

    omega = np.diag(omega_diag)
    return pd.DataFrame(omega, index=p.index, columns=p.index)


def black_litterman_posterior(
    equilibrium: pd.Series,
    cov_matrix: pd.DataFrame,
    p: pd.DataFrame,
    q: pd.Series,
    omega: pd.DataFrame,
    *,
    tau: float | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Retornos y covarianza posteriores Black-Litterman.

    μ_BL = [(τΣ)^−1 + P' Ω^−1 P]^−1 [(τΣ)^−1 π + P' Ω^−1 Q]

    Args:
        equilibrium: Prior π.
        cov_matrix: Σ anual.
        p: Matriz de views.
        q: Vector de views.
        omega: Incertidumbre de views.
        tau: Escalado del prior.

    Returns:
        (μ_BL, Σ_BL) — Σ_BL ≈ Σ (uso operativo) + ajuste ligero opcional.
    """
    tau_val = float(config.BL_TAU if tau is None else tau)
    tickers = list(cov_matrix.columns)
    pi = equilibrium.reindex(tickers).astype(float).values.reshape(-1, 1)
    sigma = cov_matrix.reindex(index=tickers, columns=tickers).astype(float).values
    p_mat = p.reindex(columns=tickers).astype(float).values
    q_vec = q.astype(float).values.reshape(-1, 1)
    omega_mat = omega.astype(float).values

    tau_sigma_inv = np.linalg.pinv(tau_val * sigma)
    omega_inv = np.linalg.pinv(omega_mat)

    left = tau_sigma_inv + p_mat.T @ omega_inv @ p_mat
    right = tau_sigma_inv @ pi + p_mat.T @ omega_inv @ q_vec
    mu_bl = np.linalg.pinv(left) @ right
    mu_series = pd.Series(mu_bl.ravel(), index=tickers, name="bl_expected_return")

    # Covarianza posterior clásica (opcional); para pesos usamos Σ original.
    sigma_bl = sigma + np.linalg.pinv(left)
    sigma_bl = 0.5 * (sigma_bl + sigma_bl.T)
    cov_bl = pd.DataFrame(sigma_bl, index=tickers, columns=tickers)
    return mu_series, cov_bl


def optimize_black_litterman_weights(
    mu_bl: pd.Series,
    cov_matrix: pd.DataFrame,
    *,
    risk_free_rate: float | None = None,
    long_only: bool | None = None,
) -> pd.Series:
    """Pesos de máximo Sharpe usando μ_BL y Σ histórica."""
    long = config.LONG_ONLY if long_only is None else long_only
    return optimization.maximum_sharpe_weights(
        mu_bl,
        cov_matrix,
        risk_free_rate=risk_free_rate,
        long_only=long,
    )


def run_black_litterman(
    expected_returns: pd.Series,
    cov_matrix: pd.DataFrame,
    views: list[dict[str, Any]],
    *,
    market_weights: pd.Series | None = None,
    fundamentals: pd.DataFrame | None = None,
    risk_free_rate: float | None = None,
    tau: float | None = None,
    delta: float | None = None,
    long_only: bool | None = None,
) -> dict[str, Any]:
    """Pipeline completo Black-Litterman + comparación con Markowitz.

    Args:
        expected_returns: μ histórica anual (referencia / Markowitz).
        cov_matrix: Σ anual.
        views: Lista de views del usuario.
        market_weights: Pesos de mercado opcionales.
        fundamentals: Para inferir market caps si no hay pesos.
        risk_free_rate: Rf anual.
        tau: Incertidumbre del prior.
        delta: Aversión al riesgo para π.
        long_only: Restricción de signos.

    Returns:
        Dict con π, μ_BL, pesos BL, pesos Markowitz, tablas comparativas.
    """
    tickers = list(expected_returns.index)
    cov = cov_matrix.reindex(index=tickers, columns=tickers)
    mu_hist = expected_returns.reindex(tickers).astype(float)
    rf = config.RISK_FREE_RATE if risk_free_rate is None else risk_free_rate
    tau_val = float(config.BL_TAU if tau is None else tau)
    delta_val = float(config.BL_DELTA if delta is None else delta)
    long = config.LONG_ONLY if long_only is None else long_only

    if market_weights is None:
        market_weights = market_weights_from_caps(tickers, fundamentals)

    w_mkt = normalize_weights(market_weights).reindex(tickers).fillna(0.0)
    pi = equilibrium_returns(cov, w_mkt, delta=delta_val)

    p, q = build_views_matrices(tickers, views)
    omega = view_uncertainty(p, cov, views, tau=tau_val)
    mu_bl, cov_bl = black_litterman_posterior(
        pi, cov, p, q, omega, tau=tau_val
    )

    w_bl = optimize_black_litterman_weights(
        mu_bl, cov, risk_free_rate=rf, long_only=long
    )
    w_markowitz = optimization.maximum_sharpe_weights(
        mu_hist, cov, risk_free_rate=rf, long_only=long
    )

    def _port_stats(weights: pd.Series, mu: pd.Series) -> dict[str, float]:
        w = weights.reindex(tickers).astype(float).values
        mu_v = mu.reindex(tickers).astype(float).values
        sig = cov.values
        ret = float(w @ mu_v)
        vol = float(np.sqrt(max(w @ sig @ w, 0.0)))
        sharpe = float((ret - rf) / vol) if vol > 0 else float("nan")
        return {"expected_return": ret, "volatility": vol, "sharpe": sharpe}

    bl_stats = _port_stats(w_bl, mu_bl)
    mk_stats = _port_stats(w_markowitz, mu_hist)

    returns_table = pd.DataFrame(
        {
            "Retorno historico": mu_hist,
            "Equilibrio (pi)": pi,
            "Retorno Black-Litterman": mu_bl,
        }
    )
    weights_table = pd.DataFrame(
        {
            "Peso mercado": w_mkt,
            "Máx. Sharpe (Markowitz)": w_markowitz.reindex(tickers),
            "Máx. Sharpe (Black-Litterman)": w_bl.reindex(tickers),
        }
    )

    return {
        "tickers": tickers,
        "tau": tau_val,
        "delta": delta_val,
        "risk_free_rate": rf,
        "market_weights": w_mkt,
        "equilibrium": pi,
        "mu_historical": mu_hist,
        "mu_bl": mu_bl,
        "cov_bl": cov_bl,
        "P": p,
        "Q": q,
        "omega": omega,
        "views": views,
        "weights_bl": w_bl,
        "weights_markowitz": w_markowitz,
        "returns_table": returns_table,
        "weights_table": weights_table,
        "bl_stats": bl_stats,
        "markowitz_stats": mk_stats,
    }


def default_views_template(tickers: list[str]) -> list[dict[str, Any]]:
    """Plantilla de views vacía / ejemplo para la UI."""
    symbols = validate_tickers(tickers)
    template = [
        {
            "type": "absoluta",
            "asset": symbols[0],
            "other": None,
            "return": 0.12,
            "confidence": config.BL_DEFAULT_CONFIDENCE,
        }
    ]
    if len(symbols) >= 2:
        template.append(
            {
                "type": "relativa",
                "asset": symbols[0],
                "other": symbols[1],
                "return": 0.02,
                "confidence": config.BL_DEFAULT_CONFIDENCE,
            }
        )
    else:
        template[0]["other"] = None
    return template
