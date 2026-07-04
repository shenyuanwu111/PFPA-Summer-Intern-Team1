# Week3 Guanming Lin Package Contents

This package contains the Week 3 automated data downloading deliverable.

## Main Files

- `src/credit_data_pipeline/`: reusable Python package for downloading and
  matching market data, SEC financials, and FRED rates.
- `finance_credit_pipeline/theory.md`: KMV/TTC theory notes and data
  requirements.
- `README.md`: setup, run, and output instructions.
- `tests/test_credit_data_pipeline.py`: regression tests for SEC extraction and
  trading-date matching.
- `sample_outputs/`: AAPL sample outputs showing expected CSV/XLSX structure.
- `requirements.txt`: Python dependencies.

## Main Run Command

```bash
PYTHONPATH=src python -m credit_data_pipeline.cli \
  --company AAPL \
  --start 2024-01-01 \
  --end 2024-12-31 \
  --out outputs/credit_data \
  --user-agent "your-name your-email@example.com"
```

The same command works with company-name queries, for example `--company Apple`
or `--company Microsoft`.

