# PFPA-Summer-Intern-Team1
Team member: Shenyuan Wu, Guanming Lin, Haixing Tan

## Stock and financial data downloader

This repository includes a Python command-line downloader that can collect, for any public company Yahoo Finance can resolve:

- stock price history
- quarterly income statement
- quarterly balance sheet
- quarterly cash flow
- current market cap metadata
- market-cap history estimated from adjusted daily close and current shares outstanding

### Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### Usage

Use ticker symbols or company names:

```powershell
python src\stock_data_downloader.py AAPL MSFT "Tesla" --period 5y --interval 1d
```

The program writes files to `data/<TICKER>/`:

- `price_history.csv`
- `quarterly_income_statement.csv`
- `quarterly_balance_sheet.csv`
- `quarterly_cash_flow.csv`
- `market_cap_history.csv`
- `summary.json`

It also writes `data/manifest.json` for all companies in the latest run.
