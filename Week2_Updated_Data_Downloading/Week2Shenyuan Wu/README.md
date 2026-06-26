# PFPA Summer Intern — Team 1
## Week 2: Automated Market Data Download

Automated pipeline to download, clean, and export market and financial data for 10 companies, ready for KMV/Merton credit risk modeling.

---

## Companies

| Ticker | Company | CIK |
|--------|---------|-----|
| COST | Costco Wholesale Corporation | 0000909832 |
| KO | The Coca-Cola Company | 0000021344 |
| DELL | Dell Technologies Inc. | 0001571996 |
| ORCL | Oracle Corporation | 0001341439 |
| PNC | PNC Financial Services Group | 0000713676 |
| WMT | Walmart Inc. | 0000104169 |
| INTU | Intuit Inc. | 0000896878 |
| AMZN | Amazon.com Inc. | 0001018724 |
| T | AT&T Inc. | 0000732717 |
| KHC | The Kraft Heinz Company | 0001637459 |

---

## Data Sources

| Data | Source | Notes |
|------|--------|-------|
| Stock price history + dividends | Yahoo Finance Chart API (direct HTTP) | No `yfinance` library — avoids rate limits |
| Balance sheet / financials | SEC EDGAR XBRL API (`data.sec.gov`) | 2 most recent annual 10-K filings per company |
| Shares outstanding | SEC EDGAR (`dei:EntityCommonStockSharesOutstanding`) | DELL: multi-class shares summed |
| 1-Year Treasury (DGS1) | FRED — `https://fred.stlouisfed.org/series/DGS1` | Primary KMV risk-free rate |
| SOFR | FRED — `https://fred.stlouisfed.org/series/SOFR` | Reference rate |
| 10-Year Treasury (DGS10) | FRED — `https://fred.stlouisfed.org/series/DGS10` | Reference only |

No API keys required for any source.

---

## Installation

```bash
pip install -r requirements.txt
```

Then open and run the notebook:

```bash
jupyter notebook PFPA_Week2_Data_Download_v3.ipynb
```

Run all cells top to bottom. Each step saves its output immediately, so partial runs are recoverable.

---

## Notebook Structure

| Step | Description |
|------|-------------|
| Step 0 | Install dependencies and imports |
| Step 1 | Configuration — tickers, CIK map, output directory |
| Step 2 | Download 2-year daily price history via Yahoo Chart API |
| Step 3 | Download annual financials and shares from SEC EDGAR XBRL |
| Step 4 | Compute daily market cap (`AdjClose_TR × Shares`) |
| Step 5 | Download risk-free rates (DGS1, SOFR, DGS10) from FRED |
| Step 6 | Build merged master dataset per company |
| Step 7 | Export to Excel (one workbook per company) |
| Step 8 | Data quality check |
| Step 9 | File summary |

---

## Output Structure

```
data/
├── risk_free_rates.csv          # Daily DGS1, SOFR, DGS10 (decimal)
├── price_history_chart.png
├── normalised_performance.png
├── market_cap_chart.png
├── risk_free_rate_chart.png
├── equity_vs_debt_chart.png
└── <TICKER>/
    ├── <TICKER>_price_history.csv   # Daily OHLCV + dividends + AdjClose_TR
    ├── <TICKER>_market_cap.csv      # Daily MarketCap_Close + MarketCap_TR
    ├── <TICKER>_financials.csv      # Annual balance sheet (2 FY, from SEC)
    ├── <TICKER>_master.csv          # Daily merged: price + market cap + rates
    └── <TICKER>_all_data.xlsx       # All of the above in one Excel workbook
```

### Key Columns

**Price history (`_price_history.csv`)**

| Column | Description |
|--------|-------------|
| `Close` | Split-adjusted closing price |
| `Dividends` | Per-share dividend paid on ex-date |
| `CumDividends` | Cumulative dividends since period start |
| `AdjClose_TR` | Total-return adjusted price = `Close + CumDividends` |

**Financials (`_financials.csv`)** — values in $mm

| Column | Description |
|--------|-------------|
| `currentDebt` | Short-term / current portion of debt |
| `currentLiabilities` | Total current liabilities |
| `longTermDebt` | Long-term debt (non-current) |
| `longTermLiabilities` | Total non-current liabilities |
| `totalDebt` | Total interest-bearing debt |
| `totalLiabilities` | All liabilities (computed as Assets − Equity if tag missing) |
| `KMV_Debt_D` | KMV debt barrier: `currentDebt + 0.5 × longTermDebt` |
| `netDebt` | `totalDebt − cashAndEquivalents` |
| `dividendPerShare` | Annual dividend per share declared |
| `dividendCash` | Total cash dividends paid ($mm) |

**Master dataset (`_master.csv`)**

| Column | Description |
|--------|-------------|
| `MarketCap_TR` | Daily equity value $E_t$ = `AdjClose_TR × Shares` |
| `RiskFreeRate` | DGS1 (decimal), forward-filled on non-trading days |
| `SOFR` | SOFR (decimal), forward-filled |

---

## Known Issues and Special Cases

**DELL — multi-class shares**
Dell has Class C and Class D shares. `EntityCommonStockSharesOutstanding` appears as two separate entries in SEC filings. The notebook sums both classes; if the SEC data is unavailable, it falls back to a hardcoded value from the 2026-06-09 10-Q filing (848,171,289 shares total).

**ORCL — long-term debt tag**
Oracle files long-term debt under `LongTermNotesPayable` rather than the standard `LongTermDebtNoncurrent`. The `FIELD_DEFS` candidate list includes this tag to capture it correctly.

**PNC — bank balance sheet**
PNC is a bank and does not report `DebtCurrent` in its 10-K. `currentDebt` will be NaN; `KMV_Debt_D` is computed from long-term debt only (`0.5 × longTermDebt`). For a full bank KMV model, short-term borrowings and deposit liabilities should be incorporated separately.

**AMZN — no dividends**
Amazon does not pay dividends. `CumDividends = 0` and `AdjClose_TR = Close` throughout.

**totalLiabilities fallback**
Where the SEC `Liabilities` XBRL tag is missing, `totalLiabilities` is computed as `totalAssets − stockholdersEquity` (accounting identity). The `_tag` column in the financials CSV records which method was used.

**SOFR history**
SOFR was introduced in April 2018. Observations before that date are NaN; this is expected behavior, not a data error.

---

## Configuration

To change tickers or settings, edit the variables at the top of **Step 1**:

```python
TICKERS       = [...]      # list of US exchange tickers
CIK_MAP       = {...}      # SEC CIK for each ticker (look up at sec.gov)
HISTORY_YEARS = 2          # years of price history
N_ANNUAL      = 2          # number of annual 10-K filings
OUTPUT_DIR    = './data'   # output root directory
```

---

## Team

PFPA Summer Intern 2026 — Team 1  
Pacific Financial Professionals Association