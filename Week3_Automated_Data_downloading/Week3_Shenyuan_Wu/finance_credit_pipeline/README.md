# KMV / TTC Credit Data Pipeline

This project has two parts:

1. A practical explanation of KMV-style market-implied credit risk versus TTC
   rating approaches.
2. A reusable Python program that downloads market prices, SEC financial
   statement data, and interest-rate series, aligns them by trading date, and
   exports CSV/XLSX files.

The code is designed to work for a U.S. public company by ticker symbol or
company-name search, subject to the availability of SEC filings and market data.

## Quick Start

From the repository root:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company AAPL \
  --start 2021-01-01 \
  --end 2024-12-31 \
  --out outputs/credit_data
```

Output files:

- `<SYMBOL>_prices.csv`
- `<SYMBOL>_financials.csv`
- `<SYMBOL>_rates.csv`
- `<SYMBOL>_matched_daily.csv`
- `<SYMBOL>_credit_inputs.xlsx`

The matched daily file uses trading dates as the panel key. Interest rates are
backward-filled from the latest available FRED observation, while financial
statement facts are matched from the latest SEC filing date. This keeps the
dataset from using accounting data before it was public.

## What the Program Downloads

| Data | Source | Notes |
|---|---|---|
| Ticker to CIK mapping | SEC `company_tickers.json` | Used to resolve SEC company facts |
| Financial statement facts | SEC XBRL Company Facts API | Assets, liabilities, debt, revenue, net income, shares, etc. |
| Daily stock prices | Yahoo chart endpoint | Adjusted close, close, volume |
| Interest rates | FRED graph CSV | Default: `DGS1`, `DGS10`; no FRED API key required |

## Core CLI Options

```text
--company       Ticker or company-name query, e.g. AAPL or Apple
--start         Start date, YYYY-MM-DD
--end           End date, YYYY-MM-DD
--out           Output folder
--rates         FRED series IDs, default: DGS1 DGS10
--user-agent    SEC-compliant user agent string
```

Prepared KMV-style fields include `market_cap_proxy`, `equity_vol_252d`,
`risk_free_rate_proxy`, `default_point_proxy`, `market_default_distance_proxy`,
and `kmv_distance_proxy`.

Prepared TTC-style fields include `book_leverage`, `current_ratio`,
`net_margin`, `return_on_assets`, `interest_coverage_proxy`, `cash_to_assets`,
and `ttc_score_proxy`.

For SEC requests, set a real user agent:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company MSFT \
  --user-agent "your-name your-email@example.com"
```

## Theory Notes

See [theory.md](theory.md) for the KMV/TTC explanation, data requirements, and
the differences between market-implied and rating-agency style credit risk.
