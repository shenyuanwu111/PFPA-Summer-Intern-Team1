from __future__ import annotations

import argparse
import json
import math
import re
from functools import lru_cache
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
import yfinance as yf


YAHOO_SEARCH_URL = "https://query2.finance.yahoo.com/v1/finance/search"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
REQUEST_HEADERS = {
    "User-Agent": "PFPA-Summer-Intern-Team1 stock data downloader contact@example.com",
}
DEFAULT_OUTPUT_DIR = Path("data")


@dataclass(frozen=True)
class DownloadSummary:
    input_company: str
    ticker: str
    company_name: str | None
    exchange: str | None
    currency: str | None
    current_market_cap: int | None
    shares_outstanding: int | None
    output_dir: str
    downloaded_at_utc: str


def clean_symbol(value: str) -> str:
    return value.strip().upper()


def looks_like_ticker(value: str) -> bool:
    return re.fullmatch(r"[A-Z0-9.^=-]{1,12}", clean_symbol(value)) is not None


def comparable_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


@lru_cache(maxsize=1)
def sec_company_tickers() -> list[dict]:
    response = requests.get(SEC_COMPANY_TICKERS_URL, headers=REQUEST_HEADERS, timeout=20)
    response.raise_for_status()
    return list(response.json().values())


def resolve_symbol_from_sec(company_or_ticker: str) -> str | None:
    query_symbol = clean_symbol(company_or_ticker)
    query_name = comparable_name(company_or_ticker)
    if not query_name:
        return None

    exact_name_match: str | None = None
    contains_name_match: str | None = None
    for company in sec_company_tickers():
        ticker = clean_symbol(company.get("ticker", ""))
        title = company.get("title", "")
        normalized_title = comparable_name(title)

        if ticker == query_symbol:
            return ticker
        if normalized_title == query_name:
            exact_name_match = ticker
        elif query_name in normalized_title and contains_name_match is None:
            contains_name_match = ticker

    return exact_name_match or contains_name_match


def resolve_symbol(company_or_ticker: str) -> str:
    query = company_or_ticker.strip()
    if not query:
        raise ValueError("Company or ticker cannot be empty.")

    if query == clean_symbol(query) and looks_like_ticker(query):
        return clean_symbol(query)

    sec_symbol = resolve_symbol_from_sec(query)
    if sec_symbol:
        return sec_symbol

    response = requests.get(
        YAHOO_SEARCH_URL,
        params={"q": query, "quotesCount": 10, "newsCount": 0, "listsCount": 0},
        headers=REQUEST_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    results = response.json().get("quotes", [])
    for quote in results:
        if quote.get("quoteType") == "EQUITY" and quote.get("symbol"):
            return clean_symbol(quote["symbol"])

    raise ValueError(f"Could not resolve '{company_or_ticker}' to a public equity ticker.")


def normalize_dataframe(frame: pd.DataFrame, index_name: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()

    normalized = frame.copy()
    normalized.index.name = index_name
    normalized = normalized.reset_index()
    return normalized


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    if frame is None or frame.empty:
        path.write_text("", encoding="utf-8")
        return
    frame.to_csv(path, index=False)


def serializable_value(value):
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def get_info(stock: yf.Ticker) -> dict:
    try:
        return stock.get_info()
    except Exception:
        return {}


def get_fast_info(stock: yf.Ticker) -> dict:
    try:
        return dict(stock.fast_info)
    except Exception:
        return {}


def pick_market_cap(info: dict, fast_info: dict) -> int | None:
    for source in (fast_info, info):
        value = source.get("marketCap") or source.get("market_cap")
        if value:
            return int(value)
    return None


def pick_shares_outstanding(info: dict, fast_info: dict) -> int | None:
    for source in (fast_info, info):
        value = source.get("shares") or source.get("sharesOutstanding") or source.get("impliedSharesOutstanding")
        if value:
            return int(value)
    return None


def build_market_cap_history(history: pd.DataFrame, shares_outstanding: int | None) -> pd.DataFrame:
    if history.empty or shares_outstanding is None:
        return pd.DataFrame()

    market_cap = history[["Close"]].copy()
    market_cap["Shares Outstanding"] = shares_outstanding
    market_cap["Market Cap"] = market_cap["Close"] * shares_outstanding
    market_cap.index.name = "Date"
    return market_cap.reset_index()


def download_company(company_or_ticker: str, output_root: Path, period: str, interval: str) -> DownloadSummary:
    symbol = resolve_symbol(company_or_ticker)
    stock = yf.Ticker(symbol)
    info = get_info(stock)
    fast_info = get_fast_info(stock)

    company_name = info.get("longName") or info.get("shortName")
    exchange = info.get("exchange") or fast_info.get("exchange")
    currency = info.get("currency") or fast_info.get("currency")
    market_cap = pick_market_cap(info, fast_info)
    shares_outstanding = pick_shares_outstanding(info, fast_info)

    company_dir = output_root / symbol
    company_dir.mkdir(parents=True, exist_ok=True)

    history = stock.history(period=period, interval=interval, auto_adjust=False)
    if not history.empty:
        history.index.name = "Date"
        history = history.reset_index()
    write_csv(history, company_dir / "price_history.csv")

    statements = {
        "quarterly_income_statement.csv": stock.quarterly_income_stmt,
        "quarterly_balance_sheet.csv": stock.quarterly_balance_sheet,
        "quarterly_cash_flow.csv": stock.quarterly_cashflow,
    }
    for filename, frame in statements.items():
        write_csv(normalize_dataframe(frame, "Metric"), company_dir / filename)

    market_cap_history = build_market_cap_history(
        history.set_index("Date") if not history.empty else pd.DataFrame(),
        shares_outstanding,
    )
    write_csv(market_cap_history, company_dir / "market_cap_history.csv")

    summary = DownloadSummary(
        input_company=company_or_ticker,
        ticker=symbol,
        company_name=serializable_value(company_name),
        exchange=serializable_value(exchange),
        currency=serializable_value(currency),
        current_market_cap=serializable_value(market_cap),
        shares_outstanding=serializable_value(shares_outstanding),
        output_dir=str(company_dir),
        downloaded_at_utc=datetime.now(timezone.utc).isoformat(),
    )
    (company_dir / "summary.json").write_text(json.dumps(asdict(summary), indent=2), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download stock price history, quarterly financials, and market-cap history."
    )
    parser.add_argument("companies", nargs="+", help="Company names or ticker symbols, for example AAPL MSFT 'Tesla'")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for downloaded CSV/JSON files.")
    parser.add_argument("--period", default="5y", help="Yahoo Finance history period, for example 1y, 5y, max.")
    parser.add_argument("--interval", default="1d", help="Yahoo Finance history interval, for example 1d, 1wk, 1mo.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    summaries: list[DownloadSummary] = []
    for company in args.companies:
        summary = download_company(company, output_root, args.period, args.interval)
        summaries.append(summary)
        print(
            f"{summary.input_company} -> {summary.ticker}: "
            f"saved price history, quarterly financials, and market-cap files to {summary.output_dir}"
        )

    manifest = [asdict(summary) for summary in summaries]
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
