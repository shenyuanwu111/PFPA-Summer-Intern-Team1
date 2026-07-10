# Week4 Guanming Lin - Independent KMV EM Implementation

This folder contains an independent implementation of the KMV/Merton
Expectation-Maximization algorithm for:

`COST`, `KO`, `DELL`, `ORCL`, `PNC`, `WMT`, `INTU`, `AMZN`, `T`, `KHC`.

The implementation follows the Week 4 paper and materials:

- Equity is modeled as a call option on firm asset value.
- The default point is proxied as short-term debt plus half of long-term debt.
- The latent asset value is inferred by inverting the Merton equity equation.
- EM loop:
  1. Initialize asset volatility from observed equity volatility and leverage.
  2. E-step: solve the hidden daily asset value by bisection.
  3. M-step: update annualized asset volatility from inferred asset log returns.
  4. Iterate until volatility converges.
- Outputs include asset value, asset return, asset volatility, distance to default,
  and expected default frequency / point-in-time probability of default.

## Files

- `kmv_em_independent.py` - self-contained algorithm implementation.
- `run_assignment.py` - runs the ten assigned companies from matched daily CSVs.
- `tests/test_kmv_em_independent.py` - focused unit tests.
- `outputs/` - generated per-company and combined results.

## Run

From this folder:

```bash
python run_assignment.py
```

By default it reads matched daily inputs from `../outputs/week4_kmv_em` and writes
results to `outputs/`.

You can override paths:

```bash
python run_assignment.py --input-dir ../outputs/week4_kmv_em --output-dir outputs
```

## Test

```bash
python -m pytest tests
```
