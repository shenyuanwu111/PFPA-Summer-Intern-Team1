# PFPA Summer Intern — Team 1
## Market-Based Credit Risk Rating Model for Public Companies

> **Pacific Financial Professionals Association**  
> Summer 2026 Internship Project

---

## Project Overview

This project builds an **AI-powered, automated credit rating system** for publicly traded companies using market data.

The underlying finance theory comes from:
- **KMV / Merton Model** — Point-In-Time (PIT) credit rating using equity as a call option on assets
- **TiC (Time-Consistent) Method** — stable Through-The-Cycle (TTC) rating developed by PFPA

The system has two main components:
1. **Data Pipeline** — automatically fetch market data for any public company
2. **Credit Assessment** — run KMV EM algorithm to produce DD, EDF (PIT PD), TiC score, and S&P letter grade

---

## Repository Structure

```
PFPA-Summer-Intern-Team1/
│
├── PFPA_Week1_Data_Download.ipynb   ← Week 1: data pipeline (this week)
│
├── data/                            ← auto-generated, not committed to git
│   ├── MSFT/
│   │   ├── MSFT_price_history.csv
│   │   ├── MSFT_balance_sheet.csv
│   │   ├── MSFT_market_cap.csv
│   │   ├── MSFT_master.csv          ← merged daily table for KMV
│   │   └── MSFT_all_data.xlsx       ← all sheets in one Excel file
│   ├── AAPL/
│   ├── TSLA/
│   └── risk_free_rates.csv
│
├── requirements.txt
└── README.md
```

---

## Week 1 — Data Download (`PFPA_Week1_Data_Download.ipynb`)

### What it does

| Step | Description | Output |
|------|-------------|--------|
| Step 0 | Install & import dependencies | — |
| Step 1 | **Configuration** — set tickers & period | — |
| Step 2 | Download **stock price history** (daily OHLCV + dividends) | `{TICKER}_price_history.csv` |
| Step 3 | Download **company info** (shares outstanding, sector, beta…) | `{TICKER}_company_info.csv` |
| Step 4 | Compute **daily market cap** = price × shares | `{TICKER}_market_cap.csv` |
| Step 5 | Download **quarterly balance sheet** (ST debt, LT debt, KMV Debt D) | `{TICKER}_balance_sheet.csv` |
| Step 6 | Download **risk-free rate** (US 13-week T-bill via `^IRX`) | `risk_free_rates.csv` |
| Step 7 | **Merge** everything into a daily master dataset | `{TICKER}_master.csv` |
| Step 8 | Export to **Excel** (one workbook, 6 sheets per company) | `{TICKER}_all_data.xlsx` |
| Step 9 | **Data quality check** — validate no missing/negative values | printed report |
| Step 10 | File summary | printed report |

### Sample output (as of June 2026)

| Ticker | Trading Days | Latest Close | Market Cap | KMV Debt D | E/D Ratio |
|--------|-------------|-------------|------------|------------|-----------|
| MSFT | 501 | $379.40 | $2.87T | $32.9B | 87.2× |
| AAPL | 501 | $298.01 | $4.41T | $47.5B | 92.8× |
| TSLA | 501 | $400.49 | $1.50T | $9.2B | 164.2× |

### KMV Debt formula used

$$D = \text{Short-term Debt} + 0.5 \times \text{Long-term Debt}$$

This follows the KMV convention from the PFPA lecture slides (slide 54).

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/shenyuanwu111/PFPA-Summer-Intern-Team1.git
cd PFPA-Summer-Intern-Team1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or just open the notebook — **Step 0** installs everything automatically.

### 3. Run the notebook

```bash
jupyter notebook PFPA_Week1_Data_Download.ipynb
```

Then: **Kernel → Restart & Run All**

### 4. Change companies

In **Step 1**, edit the `TICKERS` list:

```python
TICKERS = ['MSFT', 'AAPL', 'TSLA']   # default
```

Any US exchange ticker works. Examples:

```python
TICKERS = ['JPM', 'BAC', 'GS']       # Banks
TICKERS = ['XOM', 'CVX', 'BP']       # Energy
TICKERS = ['NVDA', 'AMD', 'INTC']    # Semiconductors
TICKERS = ['AMZN', 'WMT', 'TGT']    # Retail
```

---

## Requirements

| Package | Version | Purpose |
|---------|---------|---------|
| `yfinance` | ≥ 0.2.50 | Yahoo Finance data download |
| `pandas` | ≥ 2.0 | Data processing |
| `numpy` | ≥ 1.24 | Numerical computation |
| `matplotlib` | ≥ 3.7 | Charts |
| `openpyxl` | ≥ 3.1 | Excel export |
| `requests` | ≥ 2.28 | HTTP (used by yfinance) |

**Python**: 3.10 or higher  
**Environment**: Anaconda / conda recommended (matches our team's setup)

---

## Data Sources

| Data | Source | Ticker/API |
|------|--------|------------|
| Stock prices | Yahoo Finance | any equity ticker |
| Balance sheet | Yahoo Finance | quarterly filings |
| Shares outstanding | Yahoo Finance | `info['sharesOutstanding']` |
| 13-week T-bill rate | Yahoo Finance | `^IRX` |
| 10-year Treasury (ref) | Yahoo Finance | `^TNX` |

No API key required. All data is free via `yfinance`.

---

## Team

**PFPA Summer Intern 2026 — Team 1**  
Pacific Financial Professionals Association

Mentor: PFPA  
Repo: [github.com/shenyuanwu111/PFPA-Summer-Intern-Team1](https://github.com/shenyuanwu111/PFPA-Summer-Intern-Team1)
