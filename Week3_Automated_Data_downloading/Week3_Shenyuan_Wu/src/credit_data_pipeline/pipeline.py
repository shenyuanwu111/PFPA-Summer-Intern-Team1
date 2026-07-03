"""End-to-end orchestration for credit-risk input datasets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .downloaders import (
    DEFAULT_USER_AGENT,
    download_company_facts,
    download_fred_series,
    download_stock_prices,
    extract_financials,
    resolve_company,
)


def run_pipeline(
    company: str,
    start: str,
    end: str,
    out_dir: str | Path,
    rates: list[str] | None = None,
    user_agent: str = DEFAULT_USER_AGENT,
) -> dict[str, Path]:
    """Download, align, and save credit-risk inputs for one company."""

    rates = rates or ["DGS1", "DGS10"]
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    match = resolve_company(company, user_agent=user_agent)
    prices = download_stock_prices(match.symbol, start, end)
    facts = download_company_facts(match.cik10, user_agent=user_agent)
    financials = extract_financials(facts)
    rates_frame = download_fred_series(rates, start, end)
    matched = build_matched_daily_panel(prices, financials, rates_frame)
    data_dictionary = build_data_dictionary(matched)

    prefix = out_path / match.symbol
    paths = {
        "prices_csv": prefix.with_name(f"{match.symbol}_prices.csv"),
        "financials_csv": prefix.with_name(f"{match.symbol}_financials.csv"),
        "rates_csv": prefix.with_name(f"{match.symbol}_rates.csv"),
        "matched_csv": prefix.with_name(f"{match.symbol}_matched_daily.csv"),
        "excel": prefix.with_name(f"{match.symbol}_credit_inputs.xlsx"),
    }

    prices.to_csv(paths["prices_csv"], index=False)
    financials.to_csv(paths["financials_csv"], index=False)
    rates_frame.to_csv(paths["rates_csv"], index=False)
    matched.to_csv(paths["matched_csv"], index=False)
    save_workbook(paths["excel"], prices, financials, rates_frame, matched, data_dictionary, match.symbol, match.title)
    return paths


def build_matched_daily_panel(
    prices: pd.DataFrame,
    financials: pd.DataFrame,
    rates: pd.DataFrame,
) -> pd.DataFrame:
    """Align rates and filed financials onto trading dates using backward as-of joins."""

    panel = prices.copy()
    panel["trading_date"] = to_datetime_ns(panel["trading_date"])
    panel = panel.sort_values("trading_date")
    if not rates.empty:
        rates_sorted = rates.rename(columns={"date": "trading_date"}).copy()
        rates_sorted["trading_date"] = to_datetime_ns(rates_sorted["trading_date"])
        rates_sorted = rates_sorted.sort_values("trading_date")
        panel = pd.merge_asof(panel, rates_sorted, on="trading_date", direction="backward")

    if not financials.empty:
        fin = prepare_financials_for_daily_match(financials)
        panel = pd.merge_asof(
            panel,
            fin,
            on="trading_date",
            direction="backward",
        )

    panel = add_market_credit_fields(panel)
    return panel


def prepare_financials_for_daily_match(financials: pd.DataFrame) -> pd.DataFrame:
    """Use filing dates as the as-of key so daily rows only see public information."""

    fin = financials.copy()
    core_columns = [
        "assets",
        "liabilities",
        "current_assets",
        "current_liabilities",
        "revenue",
        "net_income",
        "operating_income",
    ]
    present_core_columns = [column for column in core_columns if column in fin.columns]
    if present_core_columns:
        fin = fin.dropna(subset=present_core_columns, how="all")

    if "filed" in fin:
        fin["trading_date"] = to_datetime_ns(fin["filed"])
    else:
        fin["trading_date"] = pd.NaT
    fin["financial_period_end"] = to_datetime_ns(fin["period_end"])
    fin["trading_date"] = fin["trading_date"].fillna(fin["financial_period_end"])
    fin = fin.dropna(subset=["trading_date"])
    fin = fin.sort_values(["trading_date", "financial_period_end"])
    return fin.drop(columns=["period_end"], errors="ignore")


def to_datetime_ns(values: pd.Series) -> pd.Series:
    return pd.to_datetime(values, errors="coerce").astype("datetime64[ns]")


def add_market_credit_fields(panel: pd.DataFrame) -> pd.DataFrame:
    frame = panel.copy()
    if "shares_outstanding" in frame:
        frame["market_cap_proxy"] = frame["adj_close"] * frame["shares_outstanding"]
    else:
        frame["market_cap_proxy"] = pd.NA

    if "dgs1" in frame:
        frame["risk_free_rate_proxy"] = frame["dgs1"] / 100.0
    elif "dgs10" in frame:
        frame["risk_free_rate_proxy"] = frame["dgs10"] / 100.0
    else:
        frame["risk_free_rate_proxy"] = pd.NA

    if {"market_cap_proxy", "default_point_proxy"}.issubset(frame.columns):
        frame["market_default_distance_proxy"] = (
            frame["market_cap_proxy"] - frame["default_point_proxy"]
        ) / frame["market_cap_proxy"]
    else:
        frame["market_default_distance_proxy"] = pd.NA

    if {"market_cap_proxy", "liabilities"}.issubset(frame.columns):
        frame["market_leverage_proxy"] = frame["liabilities"] / (frame["market_cap_proxy"] + frame["liabilities"])
    else:
        frame["market_leverage_proxy"] = pd.NA

    if {"market_default_distance_proxy", "equity_vol_252d"}.issubset(frame.columns):
        frame["kmv_distance_proxy"] = frame["market_default_distance_proxy"] / frame["equity_vol_252d"]
    else:
        frame["kmv_distance_proxy"] = pd.NA

    frame["ttc_score_proxy"] = build_ttc_score_proxy(frame)
    return frame


def build_ttc_score_proxy(frame: pd.DataFrame) -> pd.Series:
    """Create a simple transparent TTC-style score from accounting ratios."""

    score = pd.Series(0.0, index=frame.index)
    if "book_leverage" in frame:
        score += (1 - frame["book_leverage"].clip(lower=0, upper=1)).fillna(0) * 35
    if "net_margin" in frame:
        score += frame["net_margin"].clip(lower=-0.2, upper=0.3).add(0.2).div(0.5).fillna(0) * 20
    if "current_ratio" in frame:
        score += frame["current_ratio"].clip(lower=0, upper=3).div(3).fillna(0) * 15
    if "interest_coverage_proxy" in frame:
        score += frame["interest_coverage_proxy"].clip(lower=0, upper=10).div(10).fillna(0) * 20
    if "cash_to_assets" in frame:
        score += frame["cash_to_assets"].clip(lower=0, upper=0.5).div(0.5).fillna(0) * 10
    return score.round(2)


def build_data_dictionary(matched: pd.DataFrame) -> pd.DataFrame:
    descriptions = {
        "trading_date": "Stock trading date used as the daily panel key.",
        "adj_close": "Adjusted close price from Yahoo chart data.",
        "daily_return": "Daily percentage change in adjusted close.",
        "equity_vol_252d": "Annualized rolling 252-trading-day equity volatility.",
        "dgs1": "1-year Treasury yield from FRED, percent.",
        "dgs10": "10-year Treasury yield from FRED, percent.",
        "financial_period_end": "Fiscal period end of the latest matched SEC filing.",
        "filed": "SEC filing date used for as-of matching.",
        "default_point_proxy": "KMV-style default point proxy: current debt/current liabilities plus half of long-term debt.",
        "market_cap_proxy": "Adjusted close multiplied by SEC shares outstanding.",
        "risk_free_rate_proxy": "Risk-free rate proxy in decimal form, preferring DGS1 then DGS10.",
        "market_default_distance_proxy": "Market-cap cushion over default point divided by market cap.",
        "market_leverage_proxy": "Liabilities divided by market value of equity plus liabilities.",
        "kmv_distance_proxy": "Transparent KMV-style distance proxy using market cushion and equity volatility.",
        "ttc_score_proxy": "Simple through-the-cycle accounting score; higher is stronger.",
        "book_leverage": "Liabilities divided by assets.",
        "current_ratio": "Current assets divided by current liabilities.",
        "net_margin": "Net income divided by revenue.",
        "return_on_assets": "Net income divided by assets.",
        "interest_coverage_proxy": "Operating income divided by interest expense.",
        "cash_to_assets": "Cash divided by assets.",
    }
    rows = [
        {"column": column, "description": descriptions.get(column, "")}
        for column in matched.columns
    ]
    return pd.DataFrame(rows)


def save_workbook(
    path: Path,
    prices: pd.DataFrame,
    financials: pd.DataFrame,
    rates: pd.DataFrame,
    matched: pd.DataFrame,
    data_dictionary: pd.DataFrame,
    symbol: str,
    company_title: str,
) -> None:
    summary = pd.DataFrame(
        [
            ["Symbol", symbol],
            ["Company", company_title],
            ["Rows in matched daily panel", len(matched)],
            ["Financial statement match key", "SEC filing date, with fiscal period end as fallback"],
            ["Purpose", "KMV-style and TTC-style credit-risk input preparation"],
        ],
        columns=["Field", "Value"],
    )
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        prices.to_excel(writer, sheet_name="Prices", index=False)
        financials.to_excel(writer, sheet_name="Financials", index=False)
        rates.to_excel(writer, sheet_name="Rates", index=False)
        matched.to_excel(writer, sheet_name="Matched Daily", index=False)
        data_dictionary.to_excel(writer, sheet_name="Data Dictionary", index=False)
