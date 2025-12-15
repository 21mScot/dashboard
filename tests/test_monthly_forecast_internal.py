from datetime import date

import pytest

from src.config import settings
from src.core.monthly_forecast import build_monthly_forecast
from src.core.site_metrics import SiteMetrics


def _calibration_site() -> SiteMetrics:
    return SiteMetrics.from_calibration(
        miner_ths=100.0,
        miner_kw=3.0,
        start_difficulty=80e12,
        start_btc_price_usd=60000.0,
        tx_fee_btc_per_block=0.1,
    )


def _start_date() -> date:
    return getattr(settings, "FORECAST_START_DATE", date.today())


def test_higher_difficulty_growth_reduces_btc():
    site = _calibration_site()
    start_date = _start_date()

    rows_low = build_monthly_forecast(
        site=site,
        start_date=start_date,
        project_years=5,
        fee_growth_pct_per_year=0.0,
        difficulty_growth_pct_per_year=10.0,
        base_fee_btc_per_block=0.1,
    )
    rows_high = build_monthly_forecast(
        site=site,
        start_date=start_date,
        project_years=5,
        fee_growth_pct_per_year=0.0,
        difficulty_growth_pct_per_year=100.0,
        base_fee_btc_per_block=0.1,
    )

    btc_low = sum(r.btc_mined for r in rows_low)
    btc_high = sum(r.btc_mined for r in rows_high)

    assert btc_high < btc_low


def test_halving_reduces_subsidy():
    site = _calibration_site()
    start_date = _start_date()

    rows = build_monthly_forecast(
        site=site,
        start_date=start_date,
        project_years=10,
        fee_growth_pct_per_year=0.0,
        difficulty_growth_pct_per_year=0.0,
        base_fee_btc_per_block=0.1,
    )

    halving_tuple = getattr(settings, "NEXT_HALVING_DATE", None)
    if not halving_tuple:
        pytest.skip("No halving date configured")
    halving_date = date(*halving_tuple)

    before_candidates = [r for r in rows if r.month < halving_date]
    after_candidates = [r for r in rows if r.month >= halving_date]
    if not before_candidates or not after_candidates:
        pytest.skip("Forecast horizon does not cover halving")

    before = max(before_candidates, key=lambda r: r.month)
    after = min(after_candidates, key=lambda r: r.month)

    assert after.subsidy_btc == before.subsidy_btc / 2


def test_zero_diff_and_fee_growth_keeps_btc_production_flat():
    site = _calibration_site()
    start_date = _start_date()

    rows = build_monthly_forecast(
        site=site,
        start_date=start_date,
        project_years=2,
        fee_growth_pct_per_year=0.0,
        difficulty_growth_pct_per_year=0.0,
        base_fee_btc_per_block=0.1,
    )

    if not rows:
        pytest.skip("No forecast rows produced")

    year1 = sum(r.btc_mined for r in rows if r.month.year == start_date.year)
    year2 = sum(r.btc_mined for r in rows if r.month.year == start_date.year + 1)

    assert pytest.approx(year1, rel=1e-6) == year2
