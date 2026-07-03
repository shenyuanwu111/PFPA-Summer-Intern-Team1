"""CLI for downloading and aligning KMV/TTC credit-risk input data."""

from __future__ import annotations

import argparse

from .downloaders import DEFAULT_USER_AGENT
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and match credit-risk input data.")
    parser.add_argument("--company", required=True, help="Ticker or company name, e.g. AAPL or Apple")
    parser.add_argument("--start", required=True, help="Start date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date, YYYY-MM-DD")
    parser.add_argument("--out", default="outputs/credit_data", help="Output folder")
    parser.add_argument("--rates", nargs="*", default=["DGS1", "DGS10"], help="FRED rate series IDs")
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="SEC-compliant user agent, ideally 'name email@example.com'",
    )
    args = parser.parse_args()

    paths = run_pipeline(
        company=args.company,
        start=args.start,
        end=args.end,
        out_dir=args.out,
        rates=args.rates,
        user_agent=args.user_agent,
    )
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()

