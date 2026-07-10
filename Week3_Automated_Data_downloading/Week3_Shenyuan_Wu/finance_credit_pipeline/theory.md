# KMV vs TTC Credit Ratings: Theory and Data Requirements

## Terminology Note

You wrote `TiC ratings`. In credit-risk modeling, the common term is usually
`TTC`, meaning **through-the-cycle** ratings. The notes below assume TTC. If
your course or project uses `TiC` for a specific framework, treat this section
as the TTC comparison and rename as needed.

## KMV / Merton-Style Credit Risk

KMV is a structural, market-implied approach built on the Merton model. The
company's equity is treated like a call option on the firm's assets. Default is
more likely when the market value of assets falls close to or below a default
point based on liabilities.

Typical workflow:

1. Estimate market value of equity from share price and shares outstanding.
2. Estimate equity volatility from historical stock returns.
3. Infer asset value and asset volatility from equity value and volatility.
4. Define a default point, often approximated as short-term debt plus part of
   long-term debt.
5. Compute distance to default.
6. Map distance to default into an expected default frequency or risk category.

Important outputs:

- Market value of assets
- Asset volatility
- Default point
- Distance to default
- Expected default frequency proxy

Data requirements:

- Daily equity prices
- Shares outstanding or market capitalization
- Short-term and long-term liabilities
- Risk-free interest rate
- Historical lookback window for volatility
- Optional: empirical EDF mapping table

Strengths:

- Forward-looking because it uses market prices.
- Sensitive to fast changes in equity value and volatility.
- Useful for public companies with liquid traded equity.

Weaknesses:

- Harder to apply to private firms.
- Market noise can make signals volatile.
- Requires modeling assumptions to infer asset value and asset volatility.

## TTC / Through-the-Cycle Ratings

TTC ratings aim to measure credit quality across an economic cycle rather than
reacting strongly to short-term market movements. This is closer to traditional
rating-agency behavior.

Typical inputs:

- Profitability ratios
- Leverage ratios
- Liquidity ratios
- Interest coverage
- Business risk / industry risk
- Scale and diversification
- Qualitative analyst judgment
- Macroeconomic and sector assumptions

Common financial metrics:

- Debt / EBITDA
- Debt / assets
- EBIT / interest expense
- Current ratio
- Free cash flow / debt
- Revenue and margin trends

Strengths:

- More stable than market-implied signals.
- Can be applied to private firms if financial statements are available.
- Good for long-term credit policy and rating migration analysis.

Weaknesses:

- Slower to react to new market information.
- More dependent on accounting statements and rating methodology.
- Can miss rapid deterioration before financial reports update.

## Key Differences

| Dimension | KMV / Market-Implied | TTC Rating |
|---|---|---|
| Main idea | Default risk from market value and volatility of firm assets | Long-run credit quality across the cycle |
| Core data | Stock prices, market cap, liabilities, rates | Financial ratios, business risk, sector views |
| Time sensitivity | Point-in-time / fast moving | Smoothed / slower moving |
| Best for | Public companies with liquid equity | Public or private companies with financials |
| Output | Distance to default / EDF proxy | Rating grade or score |
| Main weakness | Market noise and model assumptions | Slow reaction to new information |

## Data Prepared by This Pipeline

The program does not claim to replicate the proprietary Moody's KMV EDF model.
It prepares the data needed for a KMV-style approximation and TTC-style
financial-ratio analysis:

- Daily stock prices and returns
- Rolling equity volatility
- SEC financial statement items
- Default-point proxy from liabilities
- FRED interest rates matched by trading date
- A daily matched panel for modeling or Excel review

