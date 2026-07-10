# Week 4 - KMV EM Algorithm for Assigned Companies

This folder implements a KMV/Merton Expectation-Maximization style algorithm
for the 10 assigned companies:

`COST`, `KO`, `DELL`, `ORCL`, `PNC`, `WMT`, `INTU`, `AMZN`, `T`, `KHC`.

The workflow downloads public market, financial-statement, and rate data,
matches them by trading date, estimates latent firm asset value and asset
volatility, then reports distance to default and point-in-time default
probability.

## Folder Contents

- `src/credit_data_pipeline/downloaders.py` - SEC, Yahoo, and FRED data download helpers.
- `src/credit_data_pipeline/pipeline.py` - End-to-end data matching and output generation.
- `src/credit_data_pipeline/kmv_em.py` - KMV/Merton EM algorithm implementation.
- `src/credit_data_pipeline/cli.py` - Command-line entry point.
- `tests/test_credit_data_pipeline.py` - Unit tests for data matching and EM logic.
- `outputs/week4_kmv_em/` - Generated CSV/XLSX results for the 10 assigned companies.

## Method Summary

For each company and trading date, the model uses:

- Market equity value from adjusted close price times shares outstanding.
- Default point proxy: current debt/current liabilities plus 50% of long-term debt.
- Risk-free rate proxy from FRED Treasury rates.

The EM-style loop works as follows:

1. Initialize asset volatility from observed equity volatility and leverage.
2. E-step: infer daily latent asset value by inverting the Merton equity call equation.
3. M-step: update asset volatility from inferred daily asset returns.
4. Repeat until asset volatility converges.
5. Compute distance to default and PIT default probability.

## Run

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Run all 10 assigned companies:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --assigned-companies \
  --start 2021-01-01 \
  --end 2026-07-09 \
  --out outputs/week4_kmv_em \
  --user-agent "your-name your-email@example.com"
```

Run one company:

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company COST \
  --start 2021-01-01 \
  --end 2026-07-09 \
  --out outputs/week4_kmv_em \
  --user-agent "your-name your-email@example.com"
```

## Outputs

For each ticker, the program writes:

- `<SYMBOL>_prices.csv`
- `<SYMBOL>_financials.csv`
- `<SYMBOL>_rates.csv`
- `<SYMBOL>_matched_daily.csv`
- `<SYMBOL>_kmv_em.csv`
- `<SYMBOL>_kmv_summary.csv`
- `<SYMBOL>_credit_inputs.xlsx`

The combined assignment result is:

- `outputs/week4_kmv_em/assigned_companies_kmv_summary.csv`

## Test

```bash
PYTHONPATH=src python -m pytest tests/test_credit_data_pipeline.py
```
