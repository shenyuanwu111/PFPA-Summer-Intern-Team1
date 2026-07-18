# Market-Based Credit Risk Rating Model

This project implements a market-based credit risk workflow for 10 assigned public companies:

```text
COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, KHC
```

The work has two main parts:

1. Estimate asset value, asset volatility, Distance to Default, and EDF using a KMV/Merton EM-style algorithm.
2. Generate the `Asset` sheet fields for TiC/TTC conversion using the formulas from the course PDF and the conversion workbook.

## Main Files

```text
outputs/KMV_EM_10_Companies.ipynb
outputs/Asset_TiC_TTC_conversion.ipynb
generate_em_notebook.py
generate_asset_notebook.py
requirements.txt
```

## Workflow

### 1. KMV/EM Estimation

Run:

```text
outputs/KMV_EM_10_Companies.ipynb
```

This notebook downloads and processes:

- Daily adjusted stock prices from Yahoo Finance
- Company financial facts from SEC EDGAR
- One-year Treasury rates from FRED
- Quarterly debt and shares outstanding

It then estimates:

- Asset value `A`
- Asset volatility `sigma_A`
- Distance to Default `DD`
- Expected Default Frequency `EDF`

The KMV default point is:

```text
D = short-term debt + 0.5 * long-term debt
```

### 2. Asset Sheet and TiC/TTC Conversion

Run:

```text
outputs/Asset_TiC_TTC_conversion.ipynb
```

This notebook reads the KMV/EM daily outputs and creates the `Asset` sheet format used by `TiC TTC conversion.xlsx`.

The implemented formulas are:

```text
eta_A = annualized_mean_log_asset_return + 0.5 * sigma_A^2
R = abs(eta_A - 0.5 * sigma_A^2)
CCM = sigma_A^2 / (R * ln(A / D))
mu = ln(A / D) / R
TiC Risk Score = 100 * sigma_A^2 / ln(A / D)^2
DD = (ln(A / D) + eta_A - 0.5 * sigma_A^2) / sigma_A
EDF = 1 - Phi(DD)
```

`PIT PD` is calculated using the PDF formula. `TTC PD` and `SP Rating` are generated from the `TTC` and `SP` sheets in the conversion workbook.

## Required External File

The TiC/TTC notebook expects the conversion workbook here by default:

```text
C:\Users\wujie\Downloads\TiC TTC conversion.xlsx
```

If the workbook is stored elsewhere, update this variable in the notebook:

```python
CONVERSION_WORKBOOK = Path(r"C:\Users\wujie\Downloads\TiC TTC conversion.xlsx")
```

## Outputs

The notebooks generate files under:

```text
kmv_em_output/
```

Important output files include:

```text
kmv_em_output/kmv_em_summary.csv
kmv_em_output/KMV_EM_10_companies.xlsx
kmv_em_output/asset_tic_ttc_output.csv
kmv_em_output/Asset_TiC_TTC_conversion_output.xlsx
```

Per-company daily files are also generated:

```text
kmv_em_output/<TICKER>_kmv_daily.csv
kmv_em_output/<TICKER>_em_convergence.csv
```

## Installation

Python 3.10 or newer is recommended.

Using Anaconda Prompt:

```bash
conda create -n credit-risk python=3.11
conda activate credit-risk
pip install -r requirements.txt
```

Start JupyterLab:

```bash
jupyter lab
```

Then run the notebooks in this order:

```text
1. outputs/KMV_EM_10_Companies.ipynb
2. outputs/Asset_TiC_TTC_conversion.ipynb
```

## Notes

- The model-implied `SP Rating` is not the official S&P rating.
- The model uses market-based structural credit risk formulas and a conversion table.
- Actual agency ratings include qualitative and committee-based factors such as business risk, leverage policy, industry risk, liquidity, governance, and forward-looking analyst judgment.
