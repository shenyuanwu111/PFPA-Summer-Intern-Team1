# Week 3 Automated Credit Data Downloading

This folder contains my Week 3 deliverable for automated data collection and
matching for KMV-style and TTC-style credit-risk analysis.

The program accepts either a ticker or a company-name search, resolves the
company through the SEC ticker index, downloads stock prices, SEC XBRL
financial facts, Treasury interest-rate series, matches them by trading date,
and saves CSV and Excel outputs.

## Theory Summary

KMV-style analysis is market-implied and point-in-time. It uses equity market
value, equity volatility, liabilities, and a risk-free rate to estimate a
distance-to-default style signal. It reacts quickly to market information but
requires liquid public equity and model assumptions.

TTC, or through-the-cycle, ratings focus on long-run credit quality. They rely
more on accounting ratios such as leverage, liquidity, profitability, interest
coverage, and cash coverage. They are usually more stable but slower to react
to new market stress.

Full notes are in `finance_credit_pipeline/theory.md`.

## Data Sources

- SEC company ticker index: resolves company names and ticker symbols.
- SEC company facts API: downloads XBRL accounting data from 10-K and 10-Q
  filings.
- Yahoo chart endpoint: downloads daily stock prices.
- FRED CSV endpoint: downloads Treasury yield series such as `DGS1` and
  `DGS10`.

Financial statements are matched to trading dates using the SEC `filed` date,
not just fiscal period end. This avoids using financial information before it
was publicly available.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

From this folder:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company AAPL \
  --start 2021-01-01 \
  --end 2024-12-31 \
  --out outputs/credit_data \
  --user-agent "your-name your-email@example.com"
```

`--company` can be a ticker such as `AAPL` or a company-name search such as
`Apple`.

Optional rate series can be passed with `--rates`, for example:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company Microsoft \
  --start 2022-01-01 \
  --end 2024-12-31 \
  --rates DGS1 DGS5 DGS10 \
  --out outputs/msft \
  --user-agent "your-name your-email@example.com"
```

## Outputs

For each resolved ticker, the pipeline writes:

- `<SYMBOL>_prices.csv`: daily prices, returns, and rolling equity volatility.
- `<SYMBOL>_financials.csv`: extracted SEC facts and accounting ratios.
- `<SYMBOL>_rates.csv`: requested FRED interest-rate series.
- `<SYMBOL>_matched_daily.csv`: trading-date panel with prices, rates, and the
  latest public financial data.
- `<SYMBOL>_credit_inputs.xlsx`: workbook with summary, raw data sheets,
  matched panel, and data dictionary.

## Main Prepared Fields

KMV-style fields:

- `market_cap_proxy`
- `equity_vol_252d`
- `risk_free_rate_proxy`
- `default_point_proxy`
- `market_default_distance_proxy`
- `kmv_distance_proxy`

TTC-style fields:

- `book_leverage`
- `current_ratio`
- `net_margin`
- `return_on_assets`
- `interest_coverage_proxy`
- `cash_to_assets`
- `ttc_score_proxy`

## Test

```bash
PYTHONPATH=src python -m pytest tests/test_credit_data_pipeline.py
```

