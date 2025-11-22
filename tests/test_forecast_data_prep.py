import pandas as pd

from src.core.btc_forecast_engine import MonthlyForecastRow
from src.core.forecast_utils import (
    compute_y_domain,
    prepare_btc_display,
    prepare_fiat_display,
)


def test_compute_y_domain_applies_padding():
    series = pd.Series([1.0, 2.0])
    domain = compute_y_domain(series, pad_pct=0.5)
    assert domain == (0.0, 3.0)


def test_prepare_btc_display_builds_df_and_halvings():
    rows = [
        MonthlyForecastRow(
            month=pd.Timestamp("2025-01-01").date(),
            subsidy_btc=3.0,
            fee_btc_per_block=0.0005,
            total_reward_btc_per_block=3.0005,
            btc_mined=0.1,
        )
    ]
    df, y_domain, halvings = prepare_btc_display(
        rows,
        pad_pct=0.2,
        next_halving=(2024, 4, 1),
        interval_years=4,
    )
    assert not df.empty
    assert df["Month"].dtype.kind == "M"
    assert y_domain[0] == 0.0 and y_domain[1] > 0
    assert halvings  # at least one halving date


def test_prepare_btc_display_empty_rows():
    df, y_domain, halvings = prepare_btc_display(
        [],
        pad_pct=0.2,
        next_halving=(2024, 4, 1),
        interval_years=4,
    )
    assert df.empty
    assert y_domain == (0.0, 1.0)
    assert halvings == []


def test_prepare_fiat_display_builds_df_and_halvings():
    fiat_rows = [
        {
            "Month": pd.Timestamp("2025-01-01"),
            "Revenue (GBP)": 1000.0,
            "BTC price (USD)": 50000.0,
            "BTC mined": 0.1,
        }
    ]
    df, y_domain, halvings = prepare_fiat_display(
        fiat_rows,
        pad_pct=0.3,
        next_halving=(2024, 4, 1),
        interval_years=4,
    )
    assert not df.empty
    assert df["Month"].dtype.kind == "M"
    assert y_domain[0] == 0.0 and y_domain[1] > 0
    assert halvings


def test_prepare_fiat_display_missing_month_column():
    fiat_rows = [
        {
            "Revenue (GBP)": 1000.0,
            "BTC price (USD)": 50000.0,
            "BTC mined": 0.1,
        }
    ]
    df, y_domain, halvings = prepare_fiat_display(
        fiat_rows,
        pad_pct=0.3,
        next_halving=(2024, 4, 1),
        interval_years=4,
    )
    # Month is missing, so rows are dropped -> empty result
    assert df.empty
    assert y_domain == (0.0, 1.0)
    assert halvings == []


def test_prepare_fiat_display_empty_rows():
    df, y_domain, halvings = prepare_fiat_display(
        [],
        pad_pct=0.3,
        next_halving=(2024, 4, 1),
        interval_years=4,
    )
    assert df.empty
    assert y_domain == (0.0, 1.0)
    assert halvings == []
