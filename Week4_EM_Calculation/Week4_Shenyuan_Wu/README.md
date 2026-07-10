# KMV/Merton EM Algorithm for Public Companies

This repository contains a Jupyter Notebook that estimates company asset values,
asset volatility, Distance to Default, and model-implied default probabilities
using an iterative KMV/Merton method.

The assignment is implemented for the following ten companies:

`COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, KHC`

## Main Notebook

```text
KMV_EM_10_Companies.ipynb
```

The notebook performs the complete workflow:

1. Downloads daily adjusted stock prices from Yahoo Finance.
2. Downloads company identifiers and XBRL facts from SEC EDGAR.
3. Extracts quarterly current debt, long-term debt, and shares outstanding.
4. Downloads the one-year Treasury rate (`DGS1`) from FRED.
5. Matches financial information to trading dates using SEC filing dates.
6. Calculates daily market equity value.
7. Iteratively estimates daily asset values and annualized asset volatility.
8. Calculates Distance to Default and theoretical default probability.
9. Exports detailed CSV files and a multi-sheet Excel workbook.

## Method

Equity is modeled as a call option on firm assets:

```text
E = VA * N(d1) - D * exp(-rT) * N(d2)
```

The default point is:

```text
D = Current Debt + 0.5 * Long-Term Debt
```

The algorithm starts with an asset-volatility estimate and alternates between:

- Solving the Merton equity equation for each daily asset value.
- Re-estimating annualized asset volatility from the resulting asset returns.

Iterations stop when the change in asset volatility is below the configured
tolerance or when the maximum number of iterations is reached.

## Installation

Python 3.10 or newer is recommended.

Using Anaconda Prompt:

```bash
conda create -n kmv-em python=3.11
conda activate kmv-em
pip install -r requirements.txt
```

Start JupyterLab:

```bash
jupyter lab
```

Open `KMV_EM_10_Companies.ipynb` and select **Run All**.

## Configuration

The configuration cell near the beginning of the notebook controls:

```python
TICKERS = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT",
           "INTU", "AMZN", "T", "KHC"]
YEARS = 2
T = 1.0
TRADING_DAYS = 252
MAX_ITER = 100
TOL = 1e-5
```

Change `TICKERS` to analyze another set of SEC-registered US public companies.
Before making repeated SEC requests, replace the placeholder email address in
`SEC_HEADERS` with your own contact email.

## Output

The notebook creates `kmv_em_output/` containing:

- `kmv_em_summary.csv`: company-level estimates and convergence results.
- `kmv_em_failures.csv`: companies that could not be processed.
- `<TICKER>_kmv_daily.csv`: daily market and KMV estimates.
- `<TICKER>_em_convergence.csv`: asset-volatility iteration history.
- `KMV_EM_10_companies.xlsx`: summary, daily estimates, filing inputs, and
  convergence histories in one workbook.

## Data Sources

- Yahoo Finance Chart API: daily adjusted stock prices.
- SEC EDGAR Company Facts API: quarterly debt and shares outstanding.
- SEC company ticker file: ticker-to-CIK mapping.
- Federal Reserve Bank of St. Louis FRED: one-year Treasury rate (`DGS1`).

## Validation

The notebook was executed end to end for all ten assigned companies. Each
company produced 501 complete trading-day observations. All ten estimations
converged within two or three iterations during validation.

