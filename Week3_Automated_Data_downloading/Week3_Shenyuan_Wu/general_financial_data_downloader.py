"""
General financial data downloader.

Usage examples:
    python general_financial_data_downloader.py AAPL MSFT
    python general_financial_data_downloader.py "Apple Inc" "Microsoft"

Outputs are written under ./data/<TICKER>/ by default.
"""

from __future__ import annotations

import argparse
import os
import re
import time
from datetime import datetime, timedelta
from io import StringIO
from typing import Any

import numpy as np
import pandas as pd
import requests


SEC_HEADERS = {
    "User-Agent": "PFPA research contact@example.com",
}
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}
FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


FIELD_DEFS = {
    "totalDebt": [
        "DebtLongtermAndShorttermCombinedAmount",
        "LongTermDebtAndFinanceLeaseObligationsCurrentAndNoncurrent",
        "LongTermDebtAndCapitalLeaseObligationsIncludingCurrentMaturities",
        "DebtAndCapitalLeaseObligations",
        "LongTermDebt",
    ],
    "totalLiabilities": ["Liabilities"],
    "currentDebt": [
        "DebtCurrent",
        "ShortTermBorrowings",
        "ShortTermDebt",
        "LongTermDebtCurrent",
        "LongTermDebtAndCapitalLeaseObligationsCurrent",
    ],
    "currentLiabilities": ["LiabilitiesCurrent"],
    "longTermDebt": [
        "LongTermDebtNoncurrent",
        "LongTermDebt",
        "LongTermDebtAndCapitalLeaseObligations",
        "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
        "LongTermNotesPayable",
        "SeniorNotes",
    ],
    "longTermLiabilities": ["LiabilitiesNoncurrent"],
    "dividendCash": [
        "DividendsCommonStockCash",
        "PaymentsOfDividendsCommonStock",
        "PaymentsOfDividends",
        "DividendsCash",
        "DividendsCommonStock",
        "Dividends",
    ],
    "dividendPerShare": [
        "CommonStockDividendsPerShareDeclared",
        "CommonStockDividendsPerShareCashPaid",
    ],
    "totalAssets": ["Assets"],
    "stockholdersEquity": [
        "StockholdersEquity",
        "StockholdersEquityAttributableToParent",
        "CommonStockEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
        "PartnersCapitalIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cashAndEquivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "CashAndCashEquivalents",
    ],
}


def sec_get_json(url: str) -> Any:
    resp = requests.get(url, headers=SEC_HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json()


def normalize_query(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def load_sec_company_index() -> pd.DataFrame:
    """SEC ticker to CIK/company-name mapping."""
    url = "https://www.sec.gov/files/company_tickers.json"
    data = sec_get_json(url)
    rows = list(data.values())
    df = pd.DataFrame(rows)
    df["ticker"] = df["ticker"].str.upper()
    df["cik"] = df["cik_str"].astype(int).astype(str).str.zfill(10)
    df["title_norm"] = df["title"].map(normalize_query)
    return df[["ticker", "cik", "title", "title_norm"]]


def yahoo_symbol_search(query: str) -> str | None:
    """Resolve a company name to a public equity ticker when possible."""
    url = "https://query2.finance.yahoo.com/v1/finance/search"
    params = {"q": query, "quotesCount": 10, "newsCount": 0}
    resp = requests.get(url, headers=YAHOO_HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    for item in resp.json().get("quotes", []):
        if item.get("quoteType") == "EQUITY" and item.get("symbol"):
            return str(item["symbol"]).upper()
    return None


def resolve_company(query: str, company_index: pd.DataFrame) -> dict[str, str]:
    """Accept either ticker or company name; return ticker, cik, and company name."""
    q = query.strip()
    q_upper = q.upper()

    exact_ticker = company_index[company_index["ticker"] == q_upper]
    if not exact_ticker.empty:
        row = exact_ticker.iloc[0]
        return {"ticker": row["ticker"], "cik": row["cik"], "company": row["title"]}

    q_norm = normalize_query(q)
    name_matches = company_index[company_index["title_norm"].str.contains(q_norm, regex=False)]
    if not name_matches.empty:
        row = name_matches.iloc[0]
        return {"ticker": row["ticker"], "cik": row["cik"], "company": row["title"]}

    yahoo_ticker = yahoo_symbol_search(q)
    if yahoo_ticker:
        sec_match = company_index[company_index["ticker"] == yahoo_ticker]
        if not sec_match.empty:
            row = sec_match.iloc[0]
            return {"ticker": row["ticker"], "cik": row["cik"], "company": row["title"]}

    raise ValueError(f"Could not resolve company or ticker: {query}")


def download_price_yahoo(ticker: str, years: int) -> pd.DataFrame:
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?range={years}y&interval=1d&events=history%7Cdiv%7Csplit"
    )
    resp = requests.get(url, headers=YAHOO_HEADERS, timeout=30)
    resp.raise_for_status()
    result = resp.json()["chart"]["result"][0]
    ts = result["timestamp"]
    quote = result["indicators"]["quote"][0]
    adj = result["indicators"].get("adjclose", [{}])[0].get("adjclose", [None] * len(ts))

    df = pd.DataFrame(
        {
            "Date": pd.to_datetime(ts, unit="s")
            .tz_localize("UTC")
            .tz_convert("America/New_York")
            .tz_localize(None)
            .normalize(),
            "Open": quote.get("open", [None] * len(ts)),
            "High": quote.get("high", [None] * len(ts)),
            "Low": quote.get("low", [None] * len(ts)),
            "Close": quote.get("close", [None] * len(ts)),
            "Volume": quote.get("volume", [None] * len(ts)),
            "AdjClose_Yahoo": adj,
        }
    ).set_index("Date")
    df = df.dropna(subset=["Close"]).sort_index()

    div_series = pd.Series(0.0, index=df.index)
    for event in result.get("events", {}).get("dividends", {}).values():
        d = pd.Timestamp(event["date"], unit="s").normalize()
        if d in div_series.index:
            div_series.loc[d] += float(event["amount"])
    df["Dividends"] = div_series

    split_series = pd.Series("", index=df.index, dtype="object")
    for event in result.get("events", {}).get("splits", {}).values():
        d = pd.Timestamp(event["date"], unit="s").normalize()
        if d in split_series.index:
            split_series.loc[d] = event.get("splitRatio", "")
    df["StockSplits"] = split_series
    return df


def fetch_sec_facts(cik: str) -> dict[str, Any]:
    return sec_get_json(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json")


def get_fact_units(facts: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    item = facts.get("us-gaap", {}).get(tag) or facts.get("dei", {}).get(tag)
    if not item or not item.get("units"):
        return []
    for unit in ["USD", "shares", "USD/shares", "pure"]:
        if unit in item["units"]:
            return [{**x, "unit": unit, "tag": tag} for x in item["units"][unit]]
    unit = next(iter(item["units"]))
    return [{**x, "unit": unit, "tag": tag} for x in item["units"][unit]]


def annual_rows_for_tag(facts: dict[str, Any], tag: str) -> list[dict[str, Any]]:
    rows = []
    for row in get_fact_units(facts, tag):
        if (
            row.get("form", "").startswith("10-K")
            and row.get("fy")
            and (not row.get("fp") or row.get("fp") == "FY")
            and row.get("val") is not None
        ):
            rows.append(row)
    return sorted(rows, key=lambda x: (x.get("fy") or 0, x.get("filed") or ""), reverse=True)


def pick_annual(facts: dict[str, Any], tags: list[str], fiscal_year: int) -> dict[str, Any] | None:
    for tag in tags:
        rows = [x for x in annual_rows_for_tag(facts, tag) if x.get("fy") == fiscal_year]
        if rows:
            rows.sort(key=lambda x: x.get("filed", ""), reverse=True)
            return rows[0]
    return None


def latest_annual_years(facts: dict[str, Any], n: int) -> list[int]:
    years = set()
    for tag in ["Liabilities", "Assets", "LongTermDebt", "LiabilitiesCurrent"]:
        years.update(row["fy"] for row in annual_rows_for_tag(facts, tag) if row.get("fy"))
    return sorted(years, reverse=True)[:n]


def extract_annual_financials(facts_json: dict[str, Any], ticker: str, cik: str, n_annual: int) -> pd.DataFrame:
    facts = facts_json["facts"]
    rows = []
    for fy in sorted(latest_annual_years(facts, n_annual)):
        row: dict[str, Any] = {"ticker": ticker, "cik": cik, "fiscalYear": fy}
        filed_dates = []
        period_ends = []

        for field, tags in FIELD_DEFS.items():
            fact = pick_annual(facts, tags, fy)
            if fact:
                value = abs(float(fact["val"]))
                row[field] = value if field == "dividendPerShare" else value / 1e6
                row[f"{field}_tag"] = fact["tag"]
                if fact.get("filed"):
                    filed_dates.append(fact["filed"])
                if fact.get("end"):
                    period_ends.append(fact["end"])
            else:
                row[field] = np.nan
                row[f"{field}_tag"] = ""

        if pd.isna(row["totalLiabilities"]) and pd.notna(row["totalAssets"]) and pd.notna(row["stockholdersEquity"]):
            row["totalLiabilities"] = row["totalAssets"] - row["stockholdersEquity"]
            row["totalLiabilities_tag"] = "Computed: Assets - StockholdersEquity"

        if pd.isna(row["longTermLiabilities"]) and pd.notna(row["totalLiabilities"]) and pd.notna(row["currentLiabilities"]):
            row["longTermLiabilities"] = row["totalLiabilities"] - row["currentLiabilities"]
            row["longTermLiabilities_tag"] = "Computed: Liabilities - LiabilitiesCurrent"

        row["KMV_Debt_D"] = (0 if pd.isna(row["currentDebt"]) else row["currentDebt"]) + 0.5 * (
            0 if pd.isna(row["longTermDebt"]) else row["longTermDebt"]
        )
        row["netDebt"] = (
            row["totalDebt"] - row["cashAndEquivalents"]
            if pd.notna(row["totalDebt"]) and pd.notna(row["cashAndEquivalents"])
            else np.nan
        )
        row["filedDate"] = max(filed_dates) if filed_dates else None
        row["periodEnd"] = max(period_ends) if period_ends else None
        rows.append(row)

    return pd.DataFrame(rows).sort_values(["filedDate", "fiscalYear"])


def extract_shares_history(facts_json: dict[str, Any]) -> pd.DataFrame:
    """Use filed date as availability date; sums share classes reported together."""
    facts = facts_json["facts"]
    rows = []
    for row in get_fact_units(facts, "EntityCommonStockSharesOutstanding"):
        if row.get("val") is not None and row.get("filed"):
            rows.append(
                {
                    "filedDate": row.get("filed"),
                    "periodEnd": row.get("end"),
                    "sharesOutstanding": float(row["val"]),
                    "form": row.get("form"),
                }
            )
    if not rows:
        return pd.DataFrame(columns=["filedDate", "periodEnd", "sharesOutstanding", "form"])

    df = pd.DataFrame(rows)
    grouped = (
        df.groupby(["filedDate", "periodEnd", "form"], dropna=False)["sharesOutstanding"]
        .sum()
        .reset_index()
        .sort_values("filedDate")
    )
    return grouped


def download_fred(series_id: str, years: int) -> pd.Series:
    start = (datetime.today() - timedelta(days=years * 365 + 30)).strftime("%Y-%m-%d")
    resp = requests.get(f"{FRED_BASE}?id={series_id}&observation_start={start}", timeout=30)
    resp.raise_for_status()
    df = pd.read_csv(StringIO(resp.text), index_col=0, parse_dates=True)
    s = pd.to_numeric(df.iloc[:, 0], errors="coerce").dropna()
    s.name = series_id
    return s / 100.0


def merge_asof_by_trading_date(
    trading_dates: pd.DatetimeIndex,
    dated_table: pd.DataFrame,
    date_column: str,
) -> pd.DataFrame:
    if dated_table.empty or date_column not in dated_table:
        return pd.DataFrame(index=trading_dates)
    right = dated_table.copy()
    right[date_column] = pd.to_datetime(right[date_column]).dt.normalize().astype("datetime64[ns]")
    right = right.dropna(subset=[date_column]).sort_values(date_column)
    left = pd.DataFrame({"Date": pd.to_datetime(trading_dates).normalize().astype("datetime64[ns]")}).sort_values("Date")
    merged = pd.merge_asof(left, right, left_on="Date", right_on=date_column, direction="backward")
    return merged.set_index("Date")


def build_company_dataset(query: str, company_index: pd.DataFrame, output_dir: str, years: int, n_annual: int) -> None:
    resolved = resolve_company(query, company_index)
    ticker = resolved["ticker"]
    cik = resolved["cik"]
    company = resolved["company"]
    folder = os.path.join(output_dir, ticker)
    os.makedirs(folder, exist_ok=True)

    print(f"\n[{ticker}] {company} | CIK {cik}")
    price = download_price_yahoo(ticker, years)
    facts_json = fetch_sec_facts(cik)
    financials = extract_annual_financials(facts_json, ticker, cik, n_annual)
    shares_history = extract_shares_history(facts_json)

    rf = pd.DataFrame(
        {
            "RiskFreeRate": download_fred("DGS1", years),
            "SOFR": download_fred("SOFR", years),
            "DGS10": download_fred("DGS10", years),
        }
    ).ffill()

    shares_daily = merge_asof_by_trading_date(price.index, shares_history, "filedDate")
    fin_daily = merge_asof_by_trading_date(price.index, financials, "filedDate")

    master = price.copy()
    master = master.join(rf.reindex(master.index, method="ffill"))
    if "sharesOutstanding" in shares_daily:
        master["SharesOutstanding"] = shares_daily["sharesOutstanding"]
    else:
        master["SharesOutstanding"] = np.nan
    master["MarketCap"] = master["Close"] * master["SharesOutstanding"]
    master["MarketCap_AdjYahoo"] = master["AdjClose_Yahoo"] * master["SharesOutstanding"]

    fin_cols = [
        "fiscalYear",
        "periodEnd",
        "filedDate",
        "totalDebt",
        "currentDebt",
        "longTermDebt",
        "totalLiabilities",
        "KMV_Debt_D",
        "netDebt",
        "totalAssets",
        "stockholdersEquity",
        "dividendPerShare",
        "dividendCash",
    ]
    master = master.join(fin_daily[[c for c in fin_cols if c in fin_daily.columns]], rsuffix="_financial")

    price.to_csv(os.path.join(folder, f"{ticker}_price_history.csv"))
    shares_history.to_csv(os.path.join(folder, f"{ticker}_shares_history.csv"), index=False)
    financials.to_csv(os.path.join(folder, f"{ticker}_financials_annual.csv"), index=False)
    master.to_csv(os.path.join(folder, f"{ticker}_master_daily.csv"))

    with pd.ExcelWriter(os.path.join(folder, f"{ticker}_all_data.xlsx"), engine="openpyxl") as writer:
        price.to_excel(writer, sheet_name="PriceHistory")
        shares_history.to_excel(writer, sheet_name="SharesHistory", index=False)
        financials.to_excel(writer, sheet_name="AnnualFinancials", index=False)
        rf.to_excel(writer, sheet_name="RiskFreeRates")
        master.to_excel(writer, sheet_name="MasterDaily")
        pd.DataFrame([resolved]).to_excel(writer, sheet_name="CompanyInfo", index=False)

    print(f"  saved {len(master):,} trading-day rows to {folder}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("companies", nargs="+", help="Ticker symbols or company names")
    parser.add_argument("--years", type=int, default=2)
    parser.add_argument("--annual-years", type=int, default=3)
    parser.add_argument("--output-dir", default="data")
    args = parser.parse_args()

    company_index = load_sec_company_index()
    os.makedirs(args.output_dir, exist_ok=True)

    failures = []
    for query in args.companies:
        try:
            build_company_dataset(query, company_index, args.output_dir, args.years, args.annual_years)
        except Exception as exc:
            failures.append({"query": query, "error": str(exc)})
            print(f"\n[{query}] FAILED: {exc}")
        time.sleep(0.5)

    if failures:
        pd.DataFrame(failures).to_csv(os.path.join(args.output_dir, "failures.csv"), index=False)
        print(f"\nCompleted with {len(failures)} failure(s). See failures.csv.")
    else:
        print("\nCompleted successfully.")


if __name__ == "__main__":
    main()
