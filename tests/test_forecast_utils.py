from datetime import date

from src.core.forecast_utils import build_halving_dates


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
