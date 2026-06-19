#!/usr/bin/env python3
"""
Download stock price history, quarterly financials, and market cap for companies.

Example:
    python download_financial_data.py --tickers AAPL MSFT --period 5y
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd
import yfinance as yf


DEFAULT_TICKERS = ["AAPL", "MSFT"]


DATA_FILES = {
    "price_history": "{ticker}_price_history.csv",
    "quarterly_income_statement": "{ticker}_quarterly_income_statement.csv",
    "quarterly_balance_sheet": "{ticker}_quarterly_balance_sheet.csv",
    "quarterly_cash_flow": "{ticker}_quarterly_cash_flow.csv",
    "market_cap": "{ticker}_market_cap.csv",
}


def clean_ticker(ticker: str) -> str:
    return ticker.strip().upper()


def write_csv(frame: pd.DataFrame, path: Path) -> bool:
    if frame is None or frame.empty:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path)
    return True


def existing_status(ticker: str, output_dir: Path) -> dict[str, bool]:
    company_dir = output_dir / ticker
    return {
        data_type: (company_dir / filename.format(ticker=ticker)).exists()
        for data_type, filename in DATA_FILES.items()
    }


def normalize_statement(statement: pd.DataFrame) -> pd.DataFrame:
    if statement is None or statement.empty:
        return pd.DataFrame()
    normalized = statement.copy()
    normalized.columns = [str(column.date()) if hasattr(column, "date") else str(column) for column in normalized.columns]
    return normalized


def get_market_cap(stock: yf.Ticker, ticker: str) -> pd.DataFrame:
    info = stock.get_info()
    market_cap = info.get("marketCap")
    current_price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding") or info.get("impliedSharesOutstanding")

    # If Yahoo does not return marketCap directly, estimate it from price and shares.
    if market_cap is None and current_price is not None and shares is not None:
        market_cap = current_price * shares

    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "company_name": info.get("longName") or info.get("shortName"),
                "currency": info.get("currency"),
                "current_price": current_price,
                "shares_outstanding": shares,
                "market_cap": market_cap,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": "Yahoo Finance via yfinance",
            }
        ]
    )


def download_company(ticker: str, output_dir: Path, period: str, interval: str) -> dict[str, bool]:
    ticker = clean_ticker(ticker)
    company_dir = output_dir / ticker
    stock = yf.Ticker(ticker)

    price_history = stock.history(period=period, interval=interval, auto_adjust=False)
    quarterly_income = normalize_statement(stock.quarterly_income_stmt)
    quarterly_balance = normalize_statement(stock.quarterly_balance_sheet)
    quarterly_cashflow = normalize_statement(stock.quarterly_cashflow)
    market_cap = get_market_cap(stock, ticker)

    status = {
        "price_history": write_csv(price_history, company_dir / DATA_FILES["price_history"].format(ticker=ticker)),
        "quarterly_income_statement": write_csv(quarterly_income, company_dir / DATA_FILES["quarterly_income_statement"].format(ticker=ticker)),
        "quarterly_balance_sheet": write_csv(quarterly_balance, company_dir / DATA_FILES["quarterly_balance_sheet"].format(ticker=ticker)),
        "quarterly_cash_flow": write_csv(quarterly_cashflow, company_dir / DATA_FILES["quarterly_cash_flow"].format(ticker=ticker)),
        "market_cap": write_csv(market_cap, company_dir / DATA_FILES["market_cap"].format(ticker=ticker)),
    }

    summary = pd.DataFrame([{"ticker": ticker, **status}])
    write_csv(summary, company_dir / f"{ticker}_download_summary.csv")
    return status


def build_overall_summary(results: dict[str, dict[str, bool]], output_dir: Path) -> None:
    rows = []
    for ticker, status in results.items():
        rows.append({"ticker": ticker, **status})
    pd.DataFrame(rows).to_csv(output_dir / "download_summary.csv", index=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download company stock and financial data.")
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS, help="Ticker symbols, e.g. AAPL MSFT TSLA")
    parser.add_argument("--period", default="5y", help="Price history period, e.g. 1y, 5y, max")
    parser.add_argument("--interval", default="1d", help="Price interval, e.g. 1d, 1wk, 1mo")
    parser.add_argument("--output-dir", default="data", help="Folder where downloaded CSV files will be saved")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    tickers: Iterable[str] = [clean_ticker(ticker) for ticker in args.tickers]

    results: dict[str, dict[str, bool]] = {}
    for ticker in tickers:
        print(f"Downloading {ticker}...")
        try:
            results[ticker] = download_company(ticker, output_dir, args.period, args.interval)
        except Exception as exc:
            print(f"  ERROR: {ticker}: {exc}")
            results[ticker] = existing_status(ticker, output_dir)
            if any(results[ticker].values()):
                print(f"  Using existing local CSV files for {ticker}.")

    build_overall_summary(results, output_dir)
    print(f"Done. Files saved in: {output_dir.resolve()}")
    print(pd.DataFrame([{"ticker": ticker, **status} for ticker, status in results.items()]).to_string(index=False))


if __name__ == "__main__":
    main()
