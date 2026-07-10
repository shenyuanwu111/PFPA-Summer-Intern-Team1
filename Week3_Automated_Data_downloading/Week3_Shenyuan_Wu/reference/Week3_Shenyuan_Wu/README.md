# General Financial Data Downloader

This project downloads and combines public company market data, SEC financial data, risk-free rates, and shares outstanding into CSV and Excel files.

It is designed to work from either ticker symbols or company names.

## Features

- Resolves ticker symbols and SEC CIK numbers automatically.
- Downloads daily stock price history from Yahoo Finance.
- Downloads annual financial statement facts from SEC EDGAR XBRL APIs.
- Downloads risk-free rate series from FRED.
- Extracts shares outstanding history from SEC filings.
- Matches financial statement data to trading dates using SEC filing dates.
- Exports per-company CSV files and one multi-sheet Excel workbook.

## Data Sources

- Yahoo Finance Chart API for price history, dividends, and split events.
- SEC EDGAR `company_tickers.json` for ticker-to-CIK mapping.
- SEC EDGAR company facts API for XBRL financial data.
- FRED CSV API for interest rate series.

## Installation

Create and activate a Python environment, then install dependencies:

```bash
pip install -r requirements.txt
```

Recommended Python version: Python 3.10 or newer.

## Usage

Run with one or more ticker symbols:

```bash
python general_financial_data_downloader.py AAPL MSFT AMZN
```

Run with company names:

```bash
python general_financial_data_downloader.py "Apple Inc" "Microsoft"
```

Customize the history window and annual financial years:

```bash
python general_financial_data_downloader.py AAPL --years 2 --annual-years 3
```

Choose a custom output folder:

```bash
python general_financial_data_downloader.py AAPL --output-dir data
```

## Output Files

For each company, files are saved under:

```text
data/<TICKER>/
```

Each company folder contains:

- `<TICKER>_price_history.csv`: daily OHLCV, dividends, splits, and Yahoo adjusted close.
- `<TICKER>_shares_history.csv`: shares outstanding observations from SEC filings.
- `<TICKER>_financials_annual.csv`: extracted annual financial statement fields.
- `<TICKER>_master_daily.csv`: trading-day master dataset with market data, rates, shares, market cap, and matched financial data.
- `<TICKER>_all_data.xlsx`: Excel workbook with all of the above datasets as separate sheets.

If a company fails, the script writes:

```text
data/failures.csv
```

## Master Daily Dataset

The master daily file includes:

- Daily stock price and volume.
- Dividends and split indicators.
- FRED interest rates: 1-year Treasury CMT, SOFR, and 10-year Treasury CMT.
- Shares outstanding matched by SEC filing date.
- Market capitalization based on daily close and available shares outstanding.
- Annual financial fields matched to trading dates by SEC filing date.

Using the SEC filing date helps avoid look-ahead bias. A trading day only receives financial data that had already been filed by that date.

## Validation

The script was tested with:

```bash
python general_financial_data_downloader.py AAPL --years 1 --annual-years 2 --output-dir validation_data
```

The validation run produced:

- `251` trading-day rows.
- `28` columns in `AAPL_master_daily.csv`.
- Date range: `2025-07-03` to `2026-07-02`.
- Excel sheets: `PriceHistory`, `SharesHistory`, `AnnualFinancials`, `RiskFreeRates`, `MasterDaily`, `CompanyInfo`.

## Important Notes

- The SEC recommends that automated requests include a descriptive `User-Agent`. Update `SEC_HEADERS` in the script with your name or project contact before heavy use.
- SEC XBRL tag names vary across companies and industries. The script uses a candidate tag list and fallback calculations, but some companies may still have missing fields.
- Foreign issuers, ADRs, funds, and companies with unusual reporting structures may require additional handling.
- Market cap is calculated from shares outstanding observations available from filings. This is more conservative than using one latest share count for all historical dates, but it still depends on the timing and quality of SEC share disclosures.

## Project Files

```text
general_financial_data_downloader.py
requirements.txt
README.md
```
