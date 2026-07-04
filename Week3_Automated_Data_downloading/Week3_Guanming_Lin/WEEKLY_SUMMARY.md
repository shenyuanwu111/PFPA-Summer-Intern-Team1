# Weekly Summary

This week I focused on understanding the theory and data requirements behind
KMV-style credit-risk modeling and TTC, or through-the-cycle, credit ratings.
KMV is a market-implied approach that uses stock prices, market value,
volatility, liabilities, and risk-free rates to estimate a distance-to-default
style signal. TTC ratings are more accounting-based and long-term, using
financial ratios such as leverage, liquidity, profitability, interest coverage,
and cash coverage to evaluate credit quality across an economic cycle.

After reviewing the reference materials in `Week3_Shenyuan_Wu`, I created a
separate deliverable folder, `Week3_Guanming_Lin`, under
`Week3_Automated_Data_downloading`. The folder includes theory notes, a reusable
Python package, command-line interface, requirements file, tests, sample output
files, and documentation. The program can accept either a ticker symbol or a
company-name search, resolve the company through the SEC ticker index, download
daily stock prices, retrieve SEC company financial facts, download FRED interest
rate data, and match the datasets by trading date.

The pipeline prepares the main inputs needed for both KMV-style and TTC-style
analysis. For KMV-style analysis, it creates fields such as rolling equity
volatility, market capitalization proxy, default point proxy, risk-free rate
proxy, and distance-to-default proxy. For TTC-style analysis, it extracts and
computes accounting ratios including book leverage, current ratio, net margin,
return on assets, interest coverage proxy, cash-to-assets, and a transparent
TTC score proxy.

An important design choice was matching financial statements to trading dates
using the SEC filing date instead of only the fiscal period end date. This helps
avoid look-ahead bias because the program only uses financial information after
it became publicly available. The output files include separate CSV files for
prices, financials, interest rates, and the matched daily panel, plus an Excel
workbook with summary sheets and a data dictionary.

I validated the implementation with unit tests covering SEC financial-fact
extraction, company symbol resolution, date matching, filing-date logic, and
preservation of multiple filing versions. All six tests passed. The current
pipeline is designed for U.S. public companies with available SEC and market
data. Future improvements could include adding more data vendors, supporting
private-company financial statements, improving the TTC scoring methodology, and
mapping KMV-style distance measures to empirical default probability categories.

