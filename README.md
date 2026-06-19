# PFPA-W1 Financial Data Downloader

This project automatically downloads financial data for public companies. It was created for the assignment requirement to set up AI/program tools that can automatically download stock price history, company quarterly financials, and total market capitalization for any company.

## What the Program Downloads

For any ticker symbol, the program downloads:

- Stock price history
- Quarterly income statement
- Quarterly balance sheet
- Quarterly cash flow statement
- Total market capitalization

## Data Source

The program uses Yahoo Finance through the Python package `yfinance`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run Example

Download data for Apple and Microsoft:

```bash
python download_financial_data.py --tickers AAPL MSFT --period 1y
```

Download data for more companies:

```bash
python download_financial_data.py --tickers TSLA NVDA GOOGL AMZN --period 3y
```

## Output

Downloaded CSV files are saved in the `data/` folder.

Example output files:

```text
data/AAPL/AAPL_price_history.csv
data/AAPL/AAPL_quarterly_income_statement.csv
data/AAPL/AAPL_quarterly_balance_sheet.csv
data/AAPL/AAPL_quarterly_cash_flow.csv
data/AAPL/AAPL_market_cap.csv
```

There is also a summary file:

```text
data/download_summary.csv
```

## Test Result

The program was tested with these companies:

- AAPL
- MSFT
- TSLA
- NVDA
- GOOGL
- AMZN

All required data files were downloaded successfully.

## GitHub Team Access

To work together as a team:

1. Go to the GitHub repository.
2. Open `Settings`.
3. Click `Collaborators and teams`.
4. Invite teammates by GitHub username or email.
5. Give teammates `Write` access.
6. Use branches and pull requests for teamwork.

Recommended workflow:

```bash
git checkout -b feature/my-work
git add .
git commit -m "Update project"
git push origin feature/my-work
```

Then open a pull request on GitHub and ask a teammate to review it.

## Project Files

```text
download_financial_data.py
requirements.txt
README.md
data/
```

## Assignment Requirement Covered

This project satisfies the assignment because it provides an automated way to download:

- Stock price history
- Quarterly company financials
- Total market cap

It also includes GitHub collaboration instructions for team work.
