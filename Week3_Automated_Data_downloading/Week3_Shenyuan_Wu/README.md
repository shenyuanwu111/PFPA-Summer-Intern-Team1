# KMV / TTC Credit Data Pipeline

This repository explains the theory and data requirements behind KMV-style
market-implied credit risk and TTC, or through-the-cycle, credit ratings. It
also includes a reusable Python program that can download, extract, match, and
export the main inputs needed for credit-risk analysis of a U.S. public
company.

The program accepts a ticker or company-name query, resolves the SEC CIK,
downloads stock prices, SEC XBRL financial facts, Treasury interest-rate
series, and saves matched CSV/XLSX outputs by trading date.

## Run

Install dependencies:

```bash
python -m pip install -r finance_credit_pipeline/requirements.txt
```

Run the pipeline:

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

## Outputs

For each resolved ticker, the program writes:

- `<SYMBOL>_prices.csv`: daily Yahoo stock prices, returns, and rolling equity volatility.
- `<SYMBOL>_financials.csv`: extracted SEC accounting facts and TTC-style ratios.
- `<SYMBOL>_rates.csv`: FRED interest-rate series, defaulting to `DGS1` and `DGS10`.
- `<SYMBOL>_matched_daily.csv`: stock, rate, and latest public financial data matched by trading date.
- `<SYMBOL>_credit_inputs.xlsx`: workbook with summary, raw sheets, matched panel, and data dictionary.

Financial statements are matched to trading dates using the SEC `filed` date.
This avoids using a fiscal period's numbers before they were publicly filed.

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

## Theory

See [finance_credit_pipeline/theory.md](finance_credit_pipeline/theory.md) for
the KMV/TTC comparison, data requirements, strengths, weaknesses, and why the
pipeline prepares inputs rather than claiming to reproduce Moody's proprietary
KMV EDF model.

## Test

```bash
PYTHONPATH=src python -m pytest tests/test_credit_data_pipeline.py
```

