from datetime import date

import pandas as pd

from src.core.forecast_utils import build_halving_dates, build_unified_monthly_table


def test_build_halving_dates_multiple_intervals():
    # Start in 2028-04-01, project runs beyond two halvings
    next_halving = (2028, 4, 1)
    last_month = date(2036, 12, 1)
    result = build_halving_dates(
        next_halving, interval_years=4, last_month_date=last_month
    )

    assert result == [
        date(2028, 4, 1),
        date(2032, 4, 1),
        date(2036, 4, 1),
    ]


def test_build_halving_dates_none():
    result = build_halving_dates(
        None, interval_years=4, last_month_date=date(2030, 1, 1)
    )
    assert result == []


def test_build_unified_monthly_table():
    monthly_df = pd.DataFrame(
        {
            "Month": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "BTC mined": [0.1, 0.2],
        }
    )
    fiat_df = pd.DataFrame(
        {
            "Month": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "Revenue (GBP)": [1000, 1100],
            "BTC price (USD)": [50000, 51000],
        }
    )
    result = build_unified_monthly_table(monthly_df, fiat_df, usd_to_gbp=0.8)
    assert list(result.columns) == [
        "Month",
        "BTC mined",
        "Revenue (GBP)",
        "BTC price (GBP)",
    ]
    assert result["BTC price (GBP)"].iloc[0] == 50000 * 0.8
