"""KMV/Merton asset-value estimation with an EM-style fixed-point loop."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, isfinite, log, sqrt

import numpy as np
import pandas as pd


TRADING_DAYS = 252


@dataclass(frozen=True)
class KmvEmResult:
    """Summary statistics from one KMV EM estimation run."""

    converged: bool
    iterations: int
    asset_volatility: float
    tolerance: float


def normal_cdf(value: float) -> float:
    """Standard normal cumulative distribution function."""

    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def normal_survival(value: float) -> float:
    """Standard normal upper-tail probability."""

    return 1.0 - normal_cdf(value)


def merton_equity_value(asset_value: float, default_point: float, risk_free_rate: float, asset_volatility: float, horizon: float) -> float:
    """Value equity as a call option on firm assets under the Merton model."""

    if asset_value <= 0 or default_point <= 0 or asset_volatility <= 0 or horizon <= 0:
        return np.nan
    sigma_sqrt_t = asset_volatility * sqrt(horizon)
    d1 = (log(asset_value / default_point) + (risk_free_rate + 0.5 * asset_volatility**2) * horizon) / sigma_sqrt_t
    d2 = d1 - sigma_sqrt_t
    return asset_value * normal_cdf(d1) - default_point * exp(-risk_free_rate * horizon) * normal_cdf(d2)


def solve_asset_value(
    equity_value: float,
    default_point: float,
    risk_free_rate: float,
    asset_volatility: float,
    horizon: float = 1.0,
    max_iter: int = 100,
    tolerance: float = 1e-6,
) -> float:
    """Infer asset value from observed equity value by inverting the Merton equation."""

    values = (equity_value, default_point, risk_free_rate, asset_volatility, horizon)
    if any(not isfinite(float(value)) for value in values) or equity_value <= 0 or default_point <= 0 or asset_volatility <= 0:
        return np.nan

    lower = max(equity_value, 1e-12)
    upper = max(equity_value + default_point, default_point * exp(-risk_free_rate * horizon) + equity_value)

    def objective(asset_value: float) -> float:
        return merton_equity_value(asset_value, default_point, risk_free_rate, asset_volatility, horizon) - equity_value

    while objective(upper) < 0:
        upper *= 2.0
        if upper > 1e18:
            return np.nan

    for _ in range(max_iter):
        midpoint = (lower + upper) / 2.0
        error = objective(midpoint)
        if abs(error) <= tolerance * max(equity_value, 1.0):
            return midpoint
        if error < 0:
            lower = midpoint
        else:
            upper = midpoint
    return (lower + upper) / 2.0


def estimate_kmv_em(
    panel: pd.DataFrame,
    equity_col: str = "market_cap_proxy",
    default_point_col: str = "default_point_proxy",
    risk_free_col: str = "risk_free_rate_proxy",
    date_col: str = "trading_date",
    horizon: float = 1.0,
    max_iter: int = 100,
    tolerance: float = 1e-4,
    initial_asset_volatility: float | None = None,
) -> tuple[pd.DataFrame, KmvEmResult]:
    """Estimate daily asset values, distance-to-default, and PIT PD.

    The loop follows the common practical KMV approximation:
    E-step: infer each day's latent asset value from observed equity value,
    default point, rates, and the current asset volatility estimate.
    M-step: update asset volatility from the inferred asset-return series.
    """

    required = [equity_col, default_point_col, risk_free_col]
    missing = [column for column in required if column not in panel.columns]
    if missing:
        raise ValueError(f"Missing required KMV EM columns: {', '.join(missing)}")

    frame = panel.copy()
    if date_col in frame:
        frame[date_col] = pd.to_datetime(frame[date_col], errors="coerce")
        frame = frame.sort_values(date_col)

    frame[equity_col] = pd.to_numeric(frame[equity_col], errors="coerce")
    frame[default_point_col] = pd.to_numeric(frame[default_point_col], errors="coerce")
    frame[risk_free_col] = pd.to_numeric(frame[risk_free_col], errors="coerce").fillna(0.0)

    valid = frame[equity_col].gt(0) & frame[default_point_col].gt(0)
    if valid.sum() < 3:
        raise ValueError("KMV EM requires at least three rows with positive equity value and default point")

    sigma = initial_asset_volatility or _initial_asset_volatility(frame.loc[valid, equity_col], frame.loc[valid, default_point_col])
    previous_sigma = sigma
    asset_values = pd.Series(np.nan, index=frame.index, dtype="float64")
    converged = False

    for iteration in range(1, max_iter + 1):
        for idx, row in frame.loc[valid].iterrows():
            asset_values.loc[idx] = solve_asset_value(
                equity_value=float(row[equity_col]),
                default_point=float(row[default_point_col]),
                risk_free_rate=float(row[risk_free_col]),
                asset_volatility=sigma,
                horizon=horizon,
            )

        returns = np.log(asset_values.loc[valid]).replace([np.inf, -np.inf], np.nan).diff().dropna()
        updated_sigma = float(returns.std(ddof=1) * sqrt(TRADING_DAYS)) if len(returns) >= 2 else sigma
        if not isfinite(updated_sigma) or updated_sigma <= 0:
            updated_sigma = sigma

        change = abs(updated_sigma - previous_sigma)
        sigma = updated_sigma
        if change <= tolerance:
            converged = True
            break
        previous_sigma = sigma

    frame["kmv_asset_value"] = asset_values
    frame["kmv_asset_return"] = np.log(frame["kmv_asset_value"]).replace([np.inf, -np.inf], np.nan).diff()
    frame["kmv_asset_volatility"] = sigma
    frame["kmv_distance_to_default"] = (
        np.log(frame["kmv_asset_value"] / frame[default_point_col])
        + (frame[risk_free_col] - 0.5 * sigma**2) * horizon
    ) / (sigma * sqrt(horizon))
    frame["kmv_pit_pd"] = frame["kmv_distance_to_default"].map(normal_survival)
    frame["kmv_em_converged"] = converged
    frame["kmv_em_iterations"] = iteration

    result = KmvEmResult(
        converged=converged,
        iterations=iteration,
        asset_volatility=sigma,
        tolerance=tolerance,
    )
    return frame, result


def build_kmv_summary(panel: pd.DataFrame, symbol: str, result: KmvEmResult) -> pd.DataFrame:
    """Create a compact company-level summary from an estimated KMV panel."""

    latest = panel.dropna(subset=["kmv_distance_to_default", "kmv_pit_pd"]).tail(1)
    if latest.empty:
        values = {
            "symbol": symbol,
            "latest_trading_date": pd.NaT,
            "asset_value": np.nan,
            "asset_volatility": result.asset_volatility,
            "distance_to_default": np.nan,
            "pit_pd": np.nan,
            "converged": result.converged,
            "iterations": result.iterations,
        }
    else:
        row = latest.iloc[0]
        values = {
            "symbol": symbol,
            "latest_trading_date": row.get("trading_date"),
            "asset_value": row.get("kmv_asset_value"),
            "asset_volatility": result.asset_volatility,
            "distance_to_default": row.get("kmv_distance_to_default"),
            "pit_pd": row.get("kmv_pit_pd"),
            "converged": result.converged,
            "iterations": result.iterations,
        }
    return pd.DataFrame([values])


def _initial_asset_volatility(equity_values: pd.Series, default_points: pd.Series) -> float:
    leverage_weight = equity_values / (equity_values + default_points)
    equity_returns = np.log(equity_values).replace([np.inf, -np.inf], np.nan).diff().dropna()
    equity_volatility = float(equity_returns.std(ddof=1) * sqrt(TRADING_DAYS)) if len(equity_returns) >= 2 else 0.30
    average_weight = float(leverage_weight.replace([np.inf, -np.inf], np.nan).dropna().mean())
    initial = equity_volatility * max(min(average_weight, 1.0), 0.05)
    return initial if isfinite(initial) and initial > 0 else 0.30
