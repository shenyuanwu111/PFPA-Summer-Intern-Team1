"""Independent KMV/Merton EM estimator for Week 4 credit-risk assignment."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, isfinite, log, sqrt

import numpy as np
import pandas as pd


TRADING_DAYS_PER_YEAR = 250


@dataclass(frozen=True)
class EmDiagnostics:
    converged: bool
    iterations: int
    asset_volatility: float
    last_change: float


def standard_normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def standard_normal_tail(x: float) -> float:
    return 1.0 - standard_normal_cdf(x)


def merton_equity(asset_value: float, debt: float, rate: float, sigma_asset: float, horizon_years: float = 1.0) -> float:
    """Black-Scholes-Merton equity value, treating equity as a call on assets."""

    if asset_value <= 0 or debt <= 0 or sigma_asset <= 0 or horizon_years <= 0:
        return np.nan
    sigma_t = sigma_asset * sqrt(horizon_years)
    d1 = (log(asset_value / debt) + (rate + 0.5 * sigma_asset * sigma_asset) * horizon_years) / sigma_t
    d2 = d1 - sigma_t
    return asset_value * standard_normal_cdf(d1) - debt * exp(-rate * horizon_years) * standard_normal_cdf(d2)


def infer_asset_value(equity: float, debt: float, rate: float, sigma_asset: float, horizon_years: float = 1.0) -> float:
    """Invert the Merton equity equation with a monotone bisection search."""

    if not all(isfinite(float(v)) for v in (equity, debt, rate, sigma_asset, horizon_years)):
        return np.nan
    if equity <= 0 or debt <= 0 or sigma_asset <= 0 or horizon_years <= 0:
        return np.nan

    low = max(equity, 1e-9)
    high = max(equity + debt, debt * exp(-rate * horizon_years) + equity)

    def pricing_error(asset_value: float) -> float:
        return merton_equity(asset_value, debt, rate, sigma_asset, horizon_years) - equity

    while pricing_error(high) < 0:
        high *= 2.0
        if high > 1e20:
            return np.nan

    for _ in range(120):
        mid = 0.5 * (low + high)
        error = pricing_error(mid)
        if abs(error) <= 1e-7 * max(equity, 1.0):
            return mid
        if error < 0:
            low = mid
        else:
            high = mid
    return 0.5 * (low + high)


def estimate_company_kmv(
    daily_panel: pd.DataFrame,
    equity_column: str = "market_cap_proxy",
    debt_column: str = "default_point_proxy",
    rate_column: str = "risk_free_rate_proxy",
    date_column: str = "trading_date",
    horizon_years: float = 1.0,
    max_iterations: int = 100,
    tolerance: float = 1e-4,
) -> tuple[pd.DataFrame, EmDiagnostics]:
    """Run the E-step/M-step fixed-point loop and append KMV credit metrics."""

    required = {equity_column, debt_column, rate_column}
    missing = sorted(required - set(daily_panel.columns))
    if missing:
        raise ValueError(f"Missing required input columns: {', '.join(missing)}")

    frame = daily_panel.copy()
    if date_column in frame.columns:
        frame[date_column] = pd.to_datetime(frame[date_column], errors="coerce")
        frame = frame.sort_values(date_column).reset_index(drop=True)

    for col in (equity_column, debt_column, rate_column):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame[rate_column] = frame[rate_column].fillna(0.0)

    usable = frame[equity_column].gt(0) & frame[debt_column].gt(0)
    if usable.sum() < 4:
        raise ValueError("KMV EM needs at least four rows with positive equity and debt inputs")

    sigma = initial_asset_volatility(frame.loc[usable, equity_column], frame.loc[usable, debt_column])
    asset_values = pd.Series(np.nan, index=frame.index, dtype="float64")
    converged = False
    last_change = np.inf

    for iteration in range(1, max_iterations + 1):
        for idx in frame.index[usable]:
            row = frame.loc[idx]
            asset_values.loc[idx] = infer_asset_value(
                equity=float(row[equity_column]),
                debt=float(row[debt_column]),
                rate=float(row[rate_column]),
                sigma_asset=sigma,
                horizon_years=horizon_years,
            )

        asset_log = np.log(asset_values.loc[usable]).replace([np.inf, -np.inf], np.nan)
        asset_returns = asset_log.diff().dropna()
        new_sigma = float(asset_returns.std(ddof=1) * sqrt(TRADING_DAYS_PER_YEAR)) if len(asset_returns) >= 2 else sigma
        if not isfinite(new_sigma) or new_sigma <= 0:
            new_sigma = sigma

        last_change = abs(new_sigma - sigma)
        sigma = new_sigma
        if last_change <= tolerance:
            converged = True
            break

    frame["ind_asset_value"] = asset_values
    frame["ind_asset_return"] = np.log(frame["ind_asset_value"]).replace([np.inf, -np.inf], np.nan).diff()
    frame["ind_asset_volatility"] = sigma
    frame["ind_distance_to_default"] = (
        np.log(frame["ind_asset_value"] / frame[debt_column])
        + (frame[rate_column] - 0.5 * sigma * sigma) * horizon_years
    ) / (sigma * sqrt(horizon_years))
    frame["ind_edf_pd"] = frame["ind_distance_to_default"].map(
        lambda value: standard_normal_tail(float(value)) if pd.notna(value) else np.nan
    )
    frame["ind_em_converged"] = converged
    frame["ind_em_iterations"] = iteration

    diagnostics = EmDiagnostics(
        converged=converged,
        iterations=iteration,
        asset_volatility=sigma,
        last_change=float(last_change),
    )
    return frame, diagnostics


def summarize_company(symbol: str, estimates: pd.DataFrame, diagnostics: EmDiagnostics) -> pd.DataFrame:
    valid = estimates.dropna(subset=["ind_asset_value", "ind_distance_to_default", "ind_edf_pd"])
    if valid.empty:
        row = {
            "symbol": symbol,
            "latest_trading_date": pd.NaT,
            "asset_value": np.nan,
            "asset_volatility": diagnostics.asset_volatility,
            "distance_to_default": np.nan,
            "edf_pd": np.nan,
            "converged": diagnostics.converged,
            "iterations": diagnostics.iterations,
            "last_sigma_change": diagnostics.last_change,
        }
    else:
        latest = valid.iloc[-1]
        row = {
            "symbol": symbol,
            "latest_trading_date": latest.get("trading_date"),
            "asset_value": latest["ind_asset_value"],
            "asset_volatility": diagnostics.asset_volatility,
            "distance_to_default": latest["ind_distance_to_default"],
            "edf_pd": latest["ind_edf_pd"],
            "converged": diagnostics.converged,
            "iterations": diagnostics.iterations,
            "last_sigma_change": diagnostics.last_change,
        }
    return pd.DataFrame([row])


def initial_asset_volatility(equity_values: pd.Series, debt_values: pd.Series) -> float:
    equity_log_returns = np.log(equity_values).replace([np.inf, -np.inf], np.nan).diff().dropna()
    equity_sigma = float(equity_log_returns.std(ddof=1) * sqrt(TRADING_DAYS_PER_YEAR)) if len(equity_log_returns) >= 2 else 0.30
    average_equity_share = float((equity_values / (equity_values + debt_values)).replace([np.inf, -np.inf], np.nan).mean())
    sigma = equity_sigma * min(max(average_equity_share, 0.05), 1.0)
    return sigma if isfinite(sigma) and sigma > 0 else 0.30
