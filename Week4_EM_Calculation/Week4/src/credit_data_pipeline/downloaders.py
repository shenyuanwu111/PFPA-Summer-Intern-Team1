"""Download market, financial, and rate data from public sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import io
import re
import time
from typing import Any

import pandas as pd
import requests


SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"


DEFAULT_USER_AGENT = "credit data research contact@example.com"

SPECIAL_SHARES_OUTSTANDING_BY_CIK = {
    # Dell reports multiple share classes. The project README documents this
    # 2026-05-01 10-Q fallback when EDGAR aggregation is unavailable.
    "1571996": 848_171_289,
}


@dataclass(frozen=True)
class CompanyMatch:
    symbol: str
    cik: int
    title: str

    @property
    def cik10(self) -> str:
        return str(self.cik).zfill(10)


class DownloadError(RuntimeError):
    """Raised when a required external data request fails."""


def get_json(url: str, headers: dict[str, str], params: dict[str, Any] | None = None) -> Any:
    response = request_with_retry(url, headers=headers, params=params)
    try:
        return response.json()
    except ValueError as exc:
        raise DownloadError(f"Invalid JSON from {url}") from exc


def request_with_retry(
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    attempts: int = 4,
    pause_seconds: float = 1.0,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts:
                retry_after = response.headers.get("Retry-After")
                sleep_for = float(retry_after) if retry_after else pause_seconds * attempt
                time.sleep(sleep_for)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(pause_seconds * attempt)
                continue
    raise DownloadError(f"Failed to download {url}: {last_error}")


def load_company_tickers(user_agent: str = DEFAULT_USER_AGENT) -> pd.DataFrame:
    data = get_json(SEC_TICKERS_URL, headers=sec_headers(user_agent))
    rows = list(data.values()) if isinstance(data, dict) else data
    frame = pd.DataFrame(rows)
    frame = frame.rename(columns={"ticker": "symbol", "cik_str": "cik"})
    frame["symbol"] = frame["symbol"].str.upper()
    return frame[["symbol", "cik", "title"]].sort_values("symbol").reset_index(drop=True)


def resolve_company(query: str, user_agent: str = DEFAULT_USER_AGENT) -> CompanyMatch:
    query_clean = query.strip()
    if not query_clean:
        raise DownloadError("Company query cannot be blank")

    tickers = load_company_tickers(user_agent)
    symbol_match = tickers[tickers["symbol"].str.upper() == query_clean.upper()]
    if not symbol_match.empty:
        row = symbol_match.iloc[0]
        return CompanyMatch(symbol=row["symbol"], cik=int(row["cik"]), title=row["title"])

    title_matches = tickers[tickers["title"].str.contains(query_clean, case=False, na=False, regex=False)]
    if title_matches.empty:
        raise DownloadError(f"No SEC ticker match found for {query!r}")

    normalized_query = normalize_company_name(query_clean)
    scored = title_matches.assign(
        _score=title_matches["title"].map(lambda title: company_name_score(normalized_query, title))
    )
    row = scored.sort_values(["_score", "symbol"], ascending=[False, True]).iloc[0]
    return CompanyMatch(symbol=row["symbol"], cik=int(row["cik"]), title=row["title"])


def download_company_facts(cik10: str, user_agent: str = DEFAULT_USER_AGENT) -> dict[str, Any]:
    return get_json(SEC_FACTS_URL.format(cik10=cik10), headers=sec_headers(user_agent))


def extract_financials(company_facts: dict[str, Any]) -> pd.DataFrame:
    concepts = {
        "assets": ("Assets", "AssetsCurrent"),
        "liabilities": ("Liabilities", "LiabilitiesCurrent"),
        "current_assets": ("AssetsCurrent",),
        "current_liabilities": ("LiabilitiesCurrent",),
        "long_term_debt": ("LongTermDebt", "LongTermDebtNoncurrent", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"),
        "current_debt": ("LongTermDebtCurrent", "ShortTermBorrowings", "ShortTermDebtCurrent"),
        "revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"),
        "operating_income": ("OperatingIncomeLoss",),
        "net_income": ("NetIncomeLoss", "ProfitLoss"),
        "stockholders_equity": ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
        "cash": ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
        "shares_outstanding": ("EntityCommonStockSharesOutstanding",),
        "interest_expense": ("InterestExpenseNonOperating", "InterestExpense"),
    }
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    dei = company_facts.get("facts", {}).get("dei", {})

    frames = []
    for output_name, concept_names in concepts.items():
        rows = []
        for concept in concept_names:
            fact = us_gaap.get(concept) or dei.get(concept)
            if not fact:
                continue
            unit_key = preferred_unit_key(fact.get("units", {}), output_name=output_name)
            if not unit_key:
                continue
            for item in fact["units"].get(unit_key, []):
                if item.get("form") not in {"10-K", "10-Q"}:
                    continue
                rows.append(
                    {
                        "period_end": item.get("end"),
                        "filed": item.get("filed"),
                        "form": item.get("form"),
                        "fiscal_year": item.get("fy"),
                        "fiscal_period": item.get("fp"),
                        "source_concept": concept,
                        output_name: item.get("val"),
                    }
                )
        if rows:
            frame = pd.DataFrame(rows)
            frame = frame.dropna(subset=[output_name])
            frame = frame.sort_values(["period_end", "filed", "source_concept"])
            frame = frame.drop_duplicates(
                subset=["period_end", "filed", "form", "fiscal_year", "fiscal_period"],
                keep="last",
            )
            frames.append(frame.drop(columns=["source_concept"]))

    if not frames:
        return pd.DataFrame()

    merged = frames[0]
    key_cols = ["period_end", "filed", "form", "fiscal_year", "fiscal_period"]
    for frame in frames[1:]:
        merged = pd.merge(merged, frame, on=key_cols, how="outer")

    merged["period_end"] = pd.to_datetime(merged["period_end"], errors="coerce")
    merged["filed"] = pd.to_datetime(merged["filed"], errors="coerce")
    merged = merged.dropna(subset=["period_end"])
    merged["filed"] = merged["filed"].fillna(merged["period_end"])
    merged = merged.sort_values(["period_end", "filed"]).drop_duplicates(
        subset=key_cols,
        keep="last",
    )
    cik = str(company_facts.get("cik", "")).lstrip("0")
    return add_credit_statement_fields(merged.reset_index(drop=True), cik=cik)


def preferred_unit_key(units: dict[str, Any], output_name: str | None = None) -> str | None:
    preferred = ("shares", "pure") if output_name == "shares_outstanding" else ("USD", "shares", "pure")
    for key in preferred:
        if key in units:
            return key
    return next(iter(units.keys()), None)


def add_credit_statement_fields(financials: pd.DataFrame, cik: str | None = None) -> pd.DataFrame:
    frame = financials.copy()
    for column in (
        "current_debt",
        "current_liabilities",
        "long_term_debt",
        "liabilities",
        "assets",
        "current_assets",
        "net_income",
        "operating_income",
        "revenue",
        "interest_expense",
        "cash",
    ):
        if column not in frame:
            frame[column] = pd.NA

    if "shares_outstanding" in frame:
        frame["shares_outstanding"] = frame.groupby("filed")["shares_outstanding"].transform(
            lambda values: values.bfill().ffill()
        )
        frame["shares_outstanding"] = frame["shares_outstanding"].ffill()
    elif cik in SPECIAL_SHARES_OUTSTANDING_BY_CIK:
        frame["shares_outstanding"] = SPECIAL_SHARES_OUTSTANDING_BY_CIK[cik]

    short_debt = frame["current_debt"].fillna(frame["current_liabilities"])
    long_debt = frame["long_term_debt"]
    has_debt_inputs = short_debt.notna() | long_debt.notna()
    frame["default_point_proxy"] = (short_debt.fillna(0) + 0.5 * long_debt.fillna(0)).where(has_debt_inputs)
    frame["total_debt_proxy"] = (short_debt.fillna(0) + long_debt.fillna(0)).where(has_debt_inputs)
    frame["book_leverage"] = frame["liabilities"] / frame["assets"]
    frame["current_ratio"] = frame["current_assets"] / frame["current_liabilities"]
    frame["net_margin"] = frame["net_income"] / frame["revenue"]
    frame["return_on_assets"] = frame["net_income"] / frame["assets"]
    frame["interest_coverage_proxy"] = frame["operating_income"] / frame["interest_expense"]
    frame["cash_to_assets"] = frame["cash"] / frame["assets"]
    return frame


def download_stock_prices(symbol: str, start: str, end: str) -> pd.DataFrame:
    period1 = unix_seconds(start)
    period2 = unix_seconds(end) + 24 * 60 * 60
    payload = get_json(
        YAHOO_CHART_URL.format(symbol=symbol.upper()),
        headers={"User-Agent": "Mozilla/5.0"},
        params={
            "period1": period1,
            "period2": period2,
            "interval": "1d",
            "events": "history|div|split",
        },
    )
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise DownloadError(f"No Yahoo price data returned for {symbol}")

    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    adjclose = result.get("indicators", {}).get("adjclose", [{}])[0].get("adjclose", [])
    frame = pd.DataFrame(
        {
            "trading_date": pd.to_datetime(timestamps, unit="s").date,
            "open": quote.get("open", []),
            "high": quote.get("high", []),
            "low": quote.get("low", []),
            "close": quote.get("close", []),
            "volume": quote.get("volume", []),
            "adj_close": adjclose,
        }
    )
    frame["trading_date"] = pd.to_datetime(frame["trading_date"])
    frame = frame.dropna(subset=["adj_close"]).sort_values("trading_date")
    frame["daily_return"] = frame["adj_close"].pct_change()
    frame["equity_vol_252d"] = frame["daily_return"].rolling(252, min_periods=60).std() * (252**0.5)
    return frame.reset_index(drop=True)


def download_fred_series(series_ids: list[str], start: str, end: str) -> pd.DataFrame:
    frames = []
    for series_id in series_ids:
        response = request_with_retry(FRED_CSV_URL, params={"id": series_id})
        frame = pd.read_csv(io.StringIO(response.text))
        frame = frame.rename(columns={"observation_date": "date", series_id: series_id.lower()})
        frame["date"] = pd.to_datetime(frame["date"])
        frame[series_id.lower()] = pd.to_numeric(frame[series_id.lower()].replace(".", pd.NA), errors="coerce")
        frame = frame[(frame["date"] >= pd.to_datetime(start)) & (frame["date"] <= pd.to_datetime(end))]
        frames.append(frame)

    if not frames:
        return pd.DataFrame()
    rates = frames[0]
    for frame in frames[1:]:
        rates = rates.merge(frame, on="date", how="outer")
    return rates.sort_values("date").reset_index(drop=True)


def normalize_company_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", value.lower())
    cleaned = re.sub(r"\b(inc|incorporated|corp|corporation|co|company|ltd|plc|class|common|stock)\b", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def company_name_score(normalized_query: str, title: str) -> int:
    normalized_title = normalize_company_name(title)
    if normalized_title == normalized_query:
        return 100
    if normalized_title.startswith(normalized_query):
        return 80
    query_words = set(normalized_query.split())
    title_words = set(normalized_title.split())
    return len(query_words & title_words)


def unix_seconds(value: str) -> int:
    dt = datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


def sec_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Accept-Encoding": "gzip, deflate",
    }
