import pandas as pd

from credit_data_pipeline.downloaders import extract_financials, resolve_company
from credit_data_pipeline.pipeline import build_matched_daily_panel, prepare_financials_for_daily_match


def test_extract_financials_from_sec_companyfacts_shape():
    facts = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2023,
                                "fp": "FY",
                                "val": 1000,
                            }
                        ]
                    }
                },
                "Liabilities": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2023,
                                "fp": "FY",
                                "val": 600,
                            }
                        ]
                    }
                },
                "LongTermDebt": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2023,
                                "fp": "FY",
                                "val": 200,
                            }
                        ]
                    }
                },
                "NetIncomeLoss": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2023,
                                "fp": "FY",
                                "val": 80,
                            }
                        ]
                    }
                },
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-K",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2023,
                                "fp": "FY",
                                "val": 500,
                            }
                        ]
                    }
                },
            }
        }
    }

    financials = extract_financials(facts)

    assert len(financials) == 1
    assert financials.loc[0, "assets"] == 1000
    assert financials.loc[0, "book_leverage"] == 0.6
    assert financials.loc[0, "net_margin"] == 0.16


def test_build_matched_daily_panel_uses_previous_financials_and_rates():
    prices = pd.DataFrame(
        {
            "trading_date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "adj_close": [10.0, 11.0],
            "daily_return": [None, 0.1],
            "equity_vol_252d": [None, None],
        }
    )
    rates = pd.DataFrame(
        {
            "date": pd.to_datetime(["2023-12-29", "2024-01-03"]),
            "dgs1": [5.0, 5.1],
        }
    )
    financials = pd.DataFrame(
        {
            "period_end": pd.to_datetime(["2023-12-31"]),
            "filed": pd.to_datetime(["2024-01-02"]),
            "assets": [1000],
            "liabilities": [600],
            "default_point_proxy": [300],
            "shares_outstanding": [100],
        }
    )

    matched = build_matched_daily_panel(prices, financials, rates)

    assert list(matched["dgs1"]) == [5.0, 5.1]
    assert list(matched["assets"]) == [1000, 1000]
    assert list(matched["market_cap_proxy"]) == [1000.0, 1100.0]


def test_financial_matching_uses_filing_date_not_period_end():
    prices = pd.DataFrame(
        {
            "trading_date": pd.to_datetime(["2024-01-02", "2024-02-16"]),
            "adj_close": [10.0, 12.0],
            "daily_return": [None, 0.2],
            "equity_vol_252d": [None, None],
        }
    )
    financials = pd.DataFrame(
        {
            "period_end": pd.to_datetime(["2023-12-31"]),
            "filed": pd.to_datetime(["2024-02-15"]),
            "assets": [1000],
            "liabilities": [600],
            "default_point_proxy": [300],
            "shares_outstanding": [100],
        }
    )

    matched = build_matched_daily_panel(prices, financials, pd.DataFrame())

    assert pd.isna(matched.loc[0, "assets"])
    assert matched.loc[1, "assets"] == 1000


def test_prepare_financials_falls_back_to_period_end_when_filed_missing():
    financials = pd.DataFrame(
        {
            "period_end": pd.to_datetime(["2023-12-31"]),
            "assets": [1000],
        }
    )

    prepared = prepare_financials_for_daily_match(financials)

    assert list(prepared["trading_date"]) == [pd.Timestamp("2023-12-31")]


def test_resolve_company_prefers_exact_symbol(monkeypatch):
    tickers = pd.DataFrame(
        {
            "symbol": ["APP", "AAPL"],
            "cik": [1, 2],
            "title": ["APPLOVIN CORP", "Apple Inc."],
        }
    )
    monkeypatch.setattr("credit_data_pipeline.downloaders.load_company_tickers", lambda user_agent: tickers)

    match = resolve_company("AAPL")

    assert match.symbol == "AAPL"


def test_extract_financials_preserves_multiple_filing_versions():
    facts = {
        "facts": {
            "us-gaap": {
                "Assets": {
                    "units": {
                        "USD": [
                            {
                                "form": "10-Q",
                                "end": "2023-12-31",
                                "filed": "2024-02-01",
                                "fy": 2024,
                                "fp": "Q1",
                                "val": 1000,
                            },
                            {
                                "form": "10-Q",
                                "end": "2023-12-31",
                                "filed": "2025-02-01",
                                "fy": 2025,
                                "fp": "Q1",
                                "val": 1100,
                            },
                        ]
                    }
                }
            }
        }
    }

    financials = extract_financials(facts)

    assert list(financials["filed"]) == [pd.Timestamp("2024-02-01"), pd.Timestamp("2025-02-01")]
