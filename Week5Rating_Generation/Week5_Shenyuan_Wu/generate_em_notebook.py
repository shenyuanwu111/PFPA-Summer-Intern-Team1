import json
from pathlib import Path


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)}


def code(text):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(True),
    }


cells = [
    md("""# KMV/Merton EM Algorithm for 10 Public Companies

This notebook implements the weekly assignment for:

`COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, KHC`

It downloads daily equity prices, SEC quarterly balance-sheet facts, shares outstanding, and the one-year Treasury rate. It then uses an iterative KMV/Merton procedure to estimate unobservable asset values and asset volatility.

For each trading day:

$$E_t = V_{A,t}N(d_1)-D_t e^{-r_tT}N(d_2)$$

$$d_1 = \\frac{\\ln(V_{A,t}/D_t)+(r_t+0.5\\sigma_A^2)T}{\\sigma_A\\sqrt{T}}, \\quad d_2=d_1-\\sigma_A\\sqrt{T}$$

The algorithm alternates between:

1. **E-like step:** solve the option equation for each daily asset value $V_{A,t}$ using the current $\\sigma_A$.
2. **M-like step:** update $\\sigma_A$ from the annualized volatility of estimated asset returns.

The default point follows the assignment material:

$$D_t=\\text{Current Debt}_t+0.5\\times\\text{Long-term Debt}_t$$

Financial statements are joined by **SEC filing date**, not period end, to avoid look-ahead bias.
"""),
    code("""# Run once if your environment is missing packages:
# %pip install numpy pandas requests scipy matplotlib openpyxl

from pathlib import Path
from io import StringIO
from datetime import datetime, timedelta
import math
import time

import numpy as np
import pandas as pd
import requests
import matplotlib.pyplot as plt
from scipy.optimize import brentq
from scipy.stats import norm

pd.set_option("display.max_columns", 100)
"""),
    code("""# Assignment configuration
TICKERS = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"]
YEARS = 2
T = 1.0
TRADING_DAYS = 252
MAX_ITER = 100
TOL = 1e-5
OUTPUT_DIR = Path("kmv_em_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Replace with your real email before repeated SEC requests.
SEC_HEADERS = {"User-Agent": "PFPA student research student@example.com"}
YAHOO_HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
"""),
    md("""## 1. Download and prepare point-in-time data

The code prioritizes quarterly and annual SEC filings (`10-Q` and `10-K`). A balance-sheet value only becomes available from its filing date onward. Values are kept in dollars throughout the KMV calculation.
"""),
    code("""def get_json(url, headers=None, params=None):
    response = requests.get(url, headers=headers, params=params, timeout=60)
    response.raise_for_status()
    return response.json()


def sec_company_index():
    raw = get_json("https://www.sec.gov/files/company_tickers.json", SEC_HEADERS)
    df = pd.DataFrame(raw.values())
    df["ticker"] = df["ticker"].str.upper()
    df["cik"] = df["cik_str"].astype(int).astype(str).str.zfill(10)
    return df.set_index("ticker")


def yahoo_prices(ticker, years=YEARS):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": f"{years}y", "interval": "1d", "events": "history|div|split"}
    result = get_json(url, YAHOO_HEADERS, params)["chart"]["result"][0]
    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adjusted = result["indicators"].get("adjclose", [{}])[0].get("adjclose")
    df = pd.DataFrame({
        "Date": pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("America/New_York").tz_localize(None).normalize(),
        "Close": quote["close"],
        "AdjClose": adjusted if adjusted else quote["close"],
        "Volume": quote["volume"],
    })
    return df.dropna(subset=["AdjClose"]).drop_duplicates("Date").sort_values("Date")


def fred_one_year(years=YEARS):
    start = (datetime.today() - timedelta(days=365 * years + 60)).strftime("%Y-%m-%d")
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = requests.get(url, params={"id": "DGS1", "observation_start": start}, timeout=60)
    response.raise_for_status()
    df = pd.read_csv(StringIO(response.text))
    df.columns = ["Date", "RiskFreeRate"]
    df["Date"] = pd.to_datetime(df["Date"])
    df["RiskFreeRate"] = pd.to_numeric(df["RiskFreeRate"], errors="coerce") / 100
    return df.dropna().sort_values("Date")
"""),
    code("""SHORT_DEBT_TAGS = [
    "ShortTermBorrowings", "ShortTermDebt", "DebtCurrent",
    "LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent",
    "FederalFundsPurchasedAndSecuritiesSoldUnderAgreementsToRepurchase",
    "CommercialPaper", "LiabilitiesCurrent",
]
LONG_DEBT_TAGS = [
    "LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
    "LongTermDebtAndCapitalLeaseObligations", "LongTermDebt",
]
SHARE_TAGS = ["EntityCommonStockSharesOutstanding", "WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"]


def fact_rows(company_facts, tag):
    item = company_facts.get("facts", {}).get("us-gaap", {}).get(tag)
    if item is None:
        item = company_facts.get("facts", {}).get("dei", {}).get(tag)
    if not item:
        return []
    units = item.get("units", {})
    for unit in ("USD", "shares"):
        if unit in units:
            return [{**row, "tag": tag, "unit": unit} for row in units[unit]]
    return []


def filing_facts(company_facts, tags):
    rows = []
    for priority, tag in enumerate(tags):
        for row in fact_rows(company_facts, tag):
            if row.get("form") in {"10-Q", "10-K", "10-Q/A", "10-K/A"} and row.get("filed") and row.get("end"):
                rows.append({
                    "filedDate": row["filed"], "periodEnd": row["end"],
                    "form": row["form"], "value": abs(float(row["val"])),
                    "tag": tag, "priority": priority,
                })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    # Keep the preferred tag and latest accepted fact for each filing/period.
    return (df.sort_values(["filedDate", "periodEnd", "priority"])
              .drop_duplicates(["filedDate", "periodEnd"], keep="first"))


def quarterly_debt_and_shares(company_facts):
    short = filing_facts(company_facts, SHORT_DEBT_TAGS)
    long = filing_facts(company_facts, LONG_DEBT_TAGS)
    shares = filing_facts(company_facts, SHARE_TAGS)

    frames = {}
    for df, prefix in [(short, "CurrentDebt"), (long, "LongTermDebt"), (shares, "SharesOutstanding")]:
        if not df.empty:
            frame = df[["filedDate", "periodEnd", "value", "tag"]].copy()
            frame["filedDate"] = pd.to_datetime(frame["filedDate"]).astype("datetime64[ns]")
            frame["periodEnd"] = pd.to_datetime(frame["periodEnd"]).astype("datetime64[ns]")
            frames[prefix] = frame.rename(columns={
                "periodEnd": prefix + "_periodEnd", "value": prefix, "tag": prefix + "_tag"
            }).sort_values("filedDate")
    if not frames:
        return pd.DataFrame()

    dates = sorted(set().union(*(set(frame["filedDate"]) for frame in frames.values())))
    result = pd.DataFrame({"filedDate": pd.to_datetime(dates).astype("datetime64[ns]")})
    for frame in frames.values():
        result = pd.merge_asof(result.sort_values("filedDate"), frame, on="filedDate", direction="backward")
    for column in ["CurrentDebt", "LongTermDebt", "SharesOutstanding"]:
        if column not in result:
            result[column] = np.nan
    period_columns = [c for c in result if c.endswith("_periodEnd")]
    result["periodEnd"] = result[period_columns].max(axis=1) if period_columns else pd.NaT
    result["DefaultPoint"] = result["CurrentDebt"] + 0.5 * result["LongTermDebt"]
    return result
"""),
    code("""def point_in_time_dataset(ticker, company_index, rates):
    cik = company_index.loc[ticker, "cik"]
    company = company_index.loc[ticker, "title"]
    facts = get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json", SEC_HEADERS)
    prices = yahoo_prices(ticker)
    filings = quarterly_debt_and_shares(facts)
    if filings.empty:
        raise ValueError("No usable SEC debt/share filings")

    prices["Date"] = pd.to_datetime(prices["Date"]).astype("datetime64[ns]")
    filings["filedDate"] = pd.to_datetime(filings["filedDate"]).astype("datetime64[ns]")
    rates = rates.copy()
    rates["Date"] = pd.to_datetime(rates["Date"]).astype("datetime64[ns]")

    daily = pd.merge_asof(
        prices.sort_values("Date"),
        filings.sort_values("filedDate"),
        left_on="Date", right_on="filedDate", direction="backward",
    )
    daily = pd.merge_asof(
        daily.sort_values("Date"),
        rates.sort_values("Date"),
        on="Date", direction="backward",
    )
    daily["Ticker"] = ticker
    daily["Company"] = company
    daily["EquityValue"] = daily["AdjClose"] * daily["SharesOutstanding"]
    required = ["EquityValue", "DefaultPoint", "RiskFreeRate"]
    daily = daily.dropna(subset=required)
    daily = daily[(daily["EquityValue"] > 0) & (daily["DefaultPoint"] > 0)]
    if len(daily) < 60:
        raise ValueError(f"Only {len(daily)} complete trading days")
    return daily.reset_index(drop=True), filings
"""),
    md("""## 2. KMV/Merton iterative estimation

This is often called an EM-style fixed-point algorithm in KMV assignments. Strictly speaking, it is not the textbook probabilistic EM algorithm with an explicit likelihood; it alternates between estimating latent daily asset values and updating the asset-volatility parameter.
"""),
    code("""def equity_from_assets(asset_value, debt, rate, sigma_a, horizon=T):
    vol_t = max(sigma_a * math.sqrt(horizon), 1e-10)
    d1 = (math.log(asset_value / debt) + (rate + 0.5 * sigma_a**2) * horizon) / vol_t
    d2 = d1 - vol_t
    return asset_value * norm.cdf(d1) - debt * math.exp(-rate * horizon) * norm.cdf(d2)


def solve_asset_value(equity, debt, rate, sigma_a):
    # Equity is monotone in asset value, so a bracketed root is stable.
    lower = max(equity, 1e-6)
    upper = equity + debt * math.exp(-rate * T) + 10 * debt
    fn = lambda assets: equity_from_assets(assets, debt, rate, sigma_a) - equity
    while fn(upper) < 0:
        upper *= 2
    return brentq(fn, lower, upper, xtol=1e-8, maxiter=200)


def run_kmv_em(daily, max_iter=MAX_ITER, tol=TOL):
    work = daily.copy().sort_values("Date").reset_index(drop=True)
    equity_returns = np.log(work["EquityValue"]).diff().dropna()
    sigma_e = equity_returns.std(ddof=1) * math.sqrt(TRADING_DAYS)
    leverage_weight = (work["EquityValue"] / (work["EquityValue"] + work["DefaultPoint"])).median()
    sigma_a = float(np.clip(sigma_e * leverage_weight, 0.01, 3.0))
    history = []

    for iteration in range(1, max_iter + 1):
        assets = np.array([
            solve_asset_value(e, d, r, sigma_a)
            for e, d, r in zip(work["EquityValue"], work["DefaultPoint"], work["RiskFreeRate"])
        ])
        new_sigma = float(pd.Series(np.log(assets)).diff().std(ddof=1) * math.sqrt(TRADING_DAYS))
        change = abs(new_sigma - sigma_a)
        history.append({"Iteration": iteration, "SigmaAsset": new_sigma, "AbsoluteChange": change})
        sigma_a = new_sigma
        if change < tol:
            break

    work["AssetValue"] = assets
    work["SigmaAsset"] = sigma_a
    work["d1"] = (
        np.log(work["AssetValue"] / work["DefaultPoint"])
        + (work["RiskFreeRate"] + 0.5 * sigma_a**2) * T
    ) / (sigma_a * math.sqrt(T))
    work["d2"] = work["d1"] - sigma_a * math.sqrt(T)
    work["DistanceToDefault"] = (
        np.log(work["AssetValue"] / work["DefaultPoint"])
        + (work["RiskFreeRate"] - 0.5 * sigma_a**2) * T
    ) / (sigma_a * math.sqrt(T))
    work["TheoreticalPD"] = norm.cdf(-work["DistanceToDefault"])

    summary = {
        "Ticker": work["Ticker"].iloc[0],
        "Company": work["Company"].iloc[0],
        "Observations": len(work),
        "StartDate": work["Date"].min(),
        "EndDate": work["Date"].max(),
        "SigmaEquity": sigma_e,
        "SigmaAsset": sigma_a,
        "Iterations": len(history),
        "Converged": history[-1]["AbsoluteChange"] < tol,
        "LatestAssetValue": work["AssetValue"].iloc[-1],
        "LatestDefaultPoint": work["DefaultPoint"].iloc[-1],
        "LatestDD": work["DistanceToDefault"].iloc[-1],
        "LatestTheoreticalPD": work["TheoreticalPD"].iloc[-1],
    }
    return work, pd.DataFrame(history), summary
"""),
    md("""## 3. Run the 10 assigned companies

One company failing will not stop the batch. Errors are saved separately so data-source issues can be discussed transparently.
"""),
    code("""company_index = sec_company_index()
rates = fred_one_year()

all_daily = {}
all_filings = {}
all_history = {}
summaries = []
failures = []

for ticker in TICKERS:
    print(f"Processing {ticker} ...")
    try:
        daily, filings = point_in_time_dataset(ticker, company_index, rates)
        result, history, summary = run_kmv_em(daily)
        all_daily[ticker] = result
        all_filings[ticker] = filings
        all_history[ticker] = history
        summaries.append(summary)
        print(f"  converged={summary['Converged']}, iterations={summary['Iterations']}, DD={summary['LatestDD']:.3f}")
    except Exception as exc:
        failures.append({"Ticker": ticker, "Error": str(exc)})
        print(f"  FAILED: {exc}")
    time.sleep(0.15)

summary_df = pd.DataFrame(summaries)
if not summary_df.empty:
    summary_df = summary_df.sort_values("LatestDD", ascending=False)
failure_df = pd.DataFrame(failures, columns=["Ticker", "Error"])
summary_df
"""),
    code("""# Convergence diagnostics
if all_history:
    fig, ax = plt.subplots(figsize=(10, 5))
    for ticker, history in all_history.items():
        ax.plot(history["Iteration"], history["SigmaAsset"], marker="o", ms=3, label=ticker)
    ax.set(title="KMV EM Convergence", xlabel="Iteration", ylabel="Estimated asset volatility")
    ax.grid(alpha=0.25)
    ax.legend(ncol=2)
    plt.show()
"""),
    code("""# Latest distance-to-default comparison
if not summary_df.empty:
    chart = summary_df.sort_values("LatestDD")
    colors = ["#c44e52" if value < 2 else "#4c72b0" for value in chart["LatestDD"]]
    ax = chart.plot.barh(x="Ticker", y="LatestDD", figsize=(9, 5), color=colors, legend=False)
    ax.axvline(2, color="#777777", linestyle="--", linewidth=1)
    ax.set(title="Latest KMV Distance to Default", xlabel="Distance to Default")
    plt.show()
"""),
    md("""## 4. Export reproducible results

Dollar-valued columns remain in dollars. The workbook contains summary, failures, daily KMV estimates, SEC filing inputs, and iteration histories. Separate CSV files are also written for easy grading and Git use.
"""),
    code("""summary_df.to_csv(OUTPUT_DIR / "kmv_em_summary.csv", index=False)
failure_df.to_csv(OUTPUT_DIR / "kmv_em_failures.csv", index=False)

for ticker, df in all_daily.items():
    df.to_csv(OUTPUT_DIR / f"{ticker}_kmv_daily.csv", index=False)
for ticker, df in all_history.items():
    df.to_csv(OUTPUT_DIR / f"{ticker}_em_convergence.csv", index=False)

with pd.ExcelWriter(OUTPUT_DIR / "KMV_EM_10_companies.xlsx", engine="openpyxl") as writer:
    summary_df.to_excel(writer, sheet_name="Summary", index=False)
    failure_df.to_excel(writer, sheet_name="Failures", index=False)
    for ticker, df in all_daily.items():
        df.to_excel(writer, sheet_name=f"{ticker}_Daily"[:31], index=False)
    for ticker, df in all_filings.items():
        df.to_excel(writer, sheet_name=f"{ticker}_Filings"[:31], index=False)
    for ticker, df in all_history.items():
        df.to_excel(writer, sheet_name=f"{ticker}_EM"[:31], index=False)

print(f"Saved results to: {OUTPUT_DIR.resolve()}")
"""),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.10"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

target = Path("outputs/KMV_EM_10_Companies.ipynb")
target.parent.mkdir(exist_ok=True)
target.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print(target.resolve())
