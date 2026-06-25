# Week2 - Two-Year Financials Workbook

This repository contains the Week2 two-year financial workbook for:

`COST, KO, DELL, ORCL, PNC, WMT, INTU, AMZN, T, KHC`

## Deliverable

- `Week2/outputs/financials_2026_06_24/two_year_financials.xlsx`
- `Week2/outputs/github_upload_report.pdf`

## Contents

- `Week2/work/build_financials.mjs` - Node.js builder script used to create the workbook.
- `Week2/work/create_github_upload_report_pdf.py` - Python script used to create the report PDF.
- `Week2/outputs/financials_2026_06_24/*_preview.png` - rendered workbook previews used for visual QA.
- `Week2/outputs/financials_2026_06_24/two_year_financials.xlsx` - final Excel workbook.
- `Week2/outputs/github_upload_report.pdf` - PDF report explaining the uploaded files.

## Data Sources

The workbook was built from public data:

- SEC company facts and filings for financial statement data and shares outstanding.
- FRED for one-year Treasury rate (`DGS1`) and SOFR.
- Yahoo Finance chart API for two-year closing prices and adjusted-close based dividend adjustment factors.

## Notes

- Market cap is calculated as latest closing price multiplied by shares outstanding.
- DELL shares outstanding were extracted from the latest SEC 10-Q cover-page inline XBRL and summed across common stock classes because the standard company-facts share field was unavailable.
- The workbook includes a `Sources Audit` sheet with source URLs, tags, periods, and notes.
