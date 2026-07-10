import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmv_em_independent import estimate_company_kmv, infer_asset_value, merton_equity


def test_merton_inversion_recovers_asset_value():
    asset_value = 1400.0
    debt = 800.0
    rate = 0.035
    sigma = 0.22
    equity = merton_equity(asset_value, debt, rate, sigma)

    inferred = infer_asset_value(equity, debt, rate, sigma)

    assert abs(inferred - asset_value) / asset_value < 1e-4


def test_estimator_adds_kmv_outputs():
    panel = pd.DataFrame(
        {
            "trading_date": pd.date_range("2025-01-02", periods=10, freq="B"),
            "market_cap_proxy": [1000, 1005, 1010, 1008, 1018, 1025, 1020, 1030, 1040, 1042],
            "default_point_proxy": [450] * 10,
            "risk_free_rate_proxy": [0.04] * 10,
        }
    )

    estimates, diagnostics = estimate_company_kmv(panel, tolerance=1e-3)

    assert diagnostics.iterations >= 1
    assert diagnostics.asset_volatility > 0
    assert estimates["ind_asset_value"].notna().all()
    assert estimates["ind_distance_to_default"].notna().all()
    assert estimates["ind_edf_pd"].between(0, 1).all()
