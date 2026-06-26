# PFPA Summer Intern 2026 — Team 1
## AI-Based Credit Rating Framework

> An end-to-end automation pipeline for generating market-based credit ratings for public companies, grounded in the KMV/Merton Point-in-Time (PIT) and Time-Consistent Through-the-Cycle (TiC) methodologies.

---

## Team

| Name | Role |
|------|------|
| Shenyuan Wu | Team Lead |
| Guanming Lin | Team Member |
| Haixing Tan | Team Member |

**Organization**: Pacific Financial Professionals Association (PFPA)  
**Program**: Summer Intern 2026

---

## Project Objectives

1. Develop an AI-based automation framework to generate credit ratings for public companies using market data
2. Implement the KMV Point-in-Time (PIT) approach and Time-Consistent Through-the-Cycle (TiC) credit rating methodology
3. Deploy an AI pipeline with two main components: **data access** and **credit assessment**

---

## Repository Structure

```
PFPA-Summer-Intern-Team1/
│
├── Week1 - Data Downloading/
│   └── PFPA_Week1_Data_Download.ipynb      # Initial data pipeline prototype
│
├── Week2 - Updated Data Downloading/
│   └── PFPA_Week2_Data_Download_v3.ipynb   # Production data pipeline
│
└── README.md
```

---

## Background

Credit ratings are a cornerstone of bank risk management, but methodologies vary significantly by company type and data availability. This project leverages recent advances in AI/LLM to automate the full workflow — from raw market data ingestion to final credit rating output — for publicly traded companies.

The framework covers:
- **Credit Rating**: PIT, TTC, and TiC approaches
- **Financial instruments**: Stocks, bonds, options, and option pricing
- **Balance sheet inputs**: Debt & liabilities, market cap, dividends, asset returns, risk-free rates
- **AI tooling**: LLM agents (Claude/Codex) for data access and assessment automation

---

## Theoretical Framework

### Credit Rating Approaches

| Approach | Description |
|----------|-------------|
| **PIT** (Point-in-Time) | Reflects current market conditions; responsive to the business cycle |
| **TTC** (Through-the-Cycle) | Stable long-run rating; comparable to agency ratings (Moody's, S&P) |
| **TiC** (Time-Consistent) | Hybrid: anchors PIT signals to a TTC framework for rating consistency |

### KMV / Merton Model

Equity is treated as a call option on firm assets (Merton 1974):

$$E = V_A \cdot N(d_1) - D \cdot e^{-rT} \cdot N(d_2)$$

**Distance to Default**:

$$DD = \frac{V_A - D}{\sigma_A \cdot V_A}$$

**KMV Debt Barrier**:

$$D = \text{Short-term Debt} + 0.5 \times \text{Long-term Debt}$$

---

## Data Pipeline

### Week 1 — Prototype (`Week1 - Data Downloading`)

Initial implementation using `yfinance`. Covers:
- Daily OHLCV + dividends for 3 tickers (MSFT, AAPL, TSLA)
- Quarterly balance sheet via yfinance
- 13-Week T-bill rate from Yahoo Finance
- Master dataset merge + Excel export

### Week 2 — Production (`Week2 - Updated Data Downloading`)

Rebuilt from scratch with direct HTTP sources to eliminate rate-limit issues. Covers all 10 target companies.

**Data sources (no API keys required):**

| Data | Source |
|------|--------|
| Daily price + dividends | Yahoo Finance Chart API (direct HTTP, no `yfinance`) |
| Balance sheet / financials | SEC EDGAR XBRL API (`data.sec.gov`) |
| Shares outstanding | SEC EDGAR (`dei:EntityCommonStockSharesOutstanding`) |
| 1-Year Treasury (DGS1) | FRED (`fred.stlouisfed.org`) |
| SOFR | FRED (`fred.stlouisfed.org`) |

**Companies covered:**

| Ticker | Company | SEC CIK |
|--------|---------|---------|
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

**Key computed fields:**

| Field | Formula | KMV Use |
|-------|---------|---------|
| `AdjClose_TR` | `Close + CumDividends` | Total-return adjusted price |
| `MarketCap_TR` | `AdjClose_TR × Shares` | Market equity $E_t$ |
| `KMV_Debt_D` | `CurrentDebt + 0.5 × LongTermDebt` | Default barrier $D$ |
| `RiskFreeRate` | DGS1 (decimal, forward-filled) | Risk-free rate $r$ |

**Output per company (`./data/<TICKER>/`):**
- `_price_history.csv` — daily OHLCV + dividends + `AdjClose_TR`
- `_financials.csv` — 2 fiscal years of SEC balance sheet data ($mm)
- `_market_cap.csv` — daily `MarketCap_Close` and `MarketCap_TR`
- `_master.csv` — daily merged table with rates, ready for KMV input
- `_all_data.xlsx` — all of the above in one workbook (6 sheets)

---

## Installation

```bash
git clone https://github.com/shenyuanwu111/PFPA-Summer-Intern-Team1.git
cd PFPA-Summer-Intern-Team1
pip install -r requirements.txt
jupyter notebook
```

**Dependencies:** `pandas`, `numpy`, `matplotlib`, `openpyxl`, `requests`  
No `yfinance` required.

---

## Known Special Cases

**DELL** — Two share classes (Class C + Class D). Shares are summed across both classes from SEC filings; falls back to hardcoded 10-Q value (848,171,289 shares, period 2026-05-01) if EDGAR aggregation fails.

**ORCL** — Oracle reports long-term debt under `LongTermNotesPayable` rather than standard GAAP tags. Handled via extended candidate list in `FIELD_DEFS`.

**PNC** — Bank holding company; `currentDebt` is not filed in the traditional sense. `KMV_Debt_D` currently uses long-term debt only. Full bank KMV treatment (incorporating deposit liabilities) to be addressed in Week 3.

**AMZN** — Does not pay dividends. `CumDividends = 0` and `AdjClose_TR = Close` throughout.

**`totalLiabilities` fallback** — Where the SEC `Liabilities` XBRL tag is unavailable, total liabilities are computed as `totalAssets − stockholdersEquity` (accounting identity). The `_tag` column in financials CSVs records which method was used.

---

## Weekly Progress

| Week | Focus | Status |
|------|-------|--------|
| 1 | Project setup, GitHub repo, data pipeline prototype | ✅ Done |
| 2 | Production data pipeline: Yahoo Chart API + SEC EDGAR + FRED | ✅ Done |
| 3 | KMV EM algorithm, Distance to Default, PIT probability of default | 🔄 In progress |
| 4 | TiC / TTC rating conversion, agency rating mapping | 📅 Planned |
| 5 | LLM/AI integration, rating narration, full automation | 📅 Planned |
| 6 | Testing, documentation, final presentation | 📅 Planned |

---

## References

- Merton, R.C. (1974). *On the Pricing of Corporate Debt: The Risk Structure of Interest Rates*. Journal of Finance.
- Moody's KMV. *Modeling Default Risk* (2003).
- Federal Reserve H.15 Selected Interest Rates: https://www.federalreserve.gov/releases/h15/
- WSJ Market Data (Bonds): https://www.wsj.com/market-data/bonds
- SEC EDGAR XBRL API: https://data.sec.gov/api/xbrl/companyfacts/
- FRED (Federal Reserve Bank of St. Louis): https://fred.stlouisfed.org/
