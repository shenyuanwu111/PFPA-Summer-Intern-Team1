"""Run the independent KMV EM implementation for the ten Week 4 companies."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from kmv_em_independent import estimate_company_kmv, summarize_company


ASSIGNED_COMPANIES = ["COST", "KO", "DELL", "ORCL", "PNC", "WMT", "INTU", "AMZN", "T", "KHC"]


def run_all(input_dir: Path, output_dir: Path, companies: list[str]) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    summaries = []

    for symbol in companies:
        input_path = input_dir / f"{symbol}_matched_daily.csv"
        if not input_path.exists():
            raise FileNotFoundError(f"Missing matched daily input for {symbol}: {input_path}")

        panel = pd.read_csv(input_path)
        estimates, diagnostics = estimate_company_kmv(panel)
        summary = summarize_company(symbol, estimates, diagnostics)

        estimates.to_csv(output_dir / f"{symbol}_independent_kmv_em.csv", index=False)
        summary.to_csv(output_dir / f"{symbol}_independent_kmv_summary.csv", index=False)
        summaries.append(summary)

    combined = pd.concat(summaries, ignore_index=True)
    combined.to_csv(output_dir / "assigned_companies_independent_kmv_summary.csv", index=False)
    return combined


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Independent KMV EM runner for Week 4 assigned companies.")
    default_input = Path(__file__).resolve().parents[1] / "outputs" / "week4_kmv_em"
    default_output = Path(__file__).resolve().parent / "outputs"
    parser.add_argument("--input-dir", type=Path, default=default_input)
    parser.add_argument("--output-dir", type=Path, default=default_output)
    parser.add_argument("--companies", nargs="*", default=ASSIGNED_COMPANIES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run_all(args.input_dir, args.output_dir, args.companies)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
