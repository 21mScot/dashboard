# tests/test_monthly_forecast.py

from datetime import date

from src.core.btc_forecast_engine import build_monthly_forecast, forecast_to_dataframe
from src.core.site_metrics import SiteMetrics


def _sample_site() -> SiteMetrics:
    return SiteMetrics(
        asics_supported=10,
        power_per_asic_kw=3.0,
        site_power_used_kw=30.0,
        site_power_available_kw=30.0,
        spare_capacity_kw=0.0,
        site_btc_per_day=0.01,
        site_revenue_usd_per_day=300.0,
        site_revenue_gbp_per_day=240.0,
        site_power_cost_gbp_per_day=50.0,
        site_net_revenue_gbp_per_day=190.0,
        net_revenue_per_kw_gbp_per_day=6.33,
        net_revenue_per_kwh_gbp=0.264,
    )


def test_forecast_respects_halving_and_duration():
    site = _sample_site()
    start = date(2028, 3, 1)
    rows = build_monthly_forecast(
        site=site,
        start_date=start,
        project_years=1,
        fee_growth_pct_per_year=0.0,
        base_fee_btc_per_block=0.0,
        hashrate_growth_pct_per_year=0.0,
    )
    assert len(rows) == 12
    # After halving date (2028-04-01 default), subsidy should halve
    pre = next(r for r in rows if r.month == date(2028, 3, 1))
    post = next(r for r in rows if r.month == date(2028, 4, 1))
    assert post.subsidy_btc == pre.subsidy_btc * 0.5


def test_forecast_to_dataframe_shape():
    site = _sample_site()
    rows = build_monthly_forecast(
        site=site,
        start_date=date.today(),
        project_years=1,
        fee_growth_pct_per_year=5.0,
    )
    df = forecast_to_dataframe(rows)
    assert not df.empty
    assert set(df.columns) == {
        "Month",
        "Subsidy (BTC)",
        "Fee (BTC/block)",
        "Total reward (BTC/block)",
        "BTC mined",
    }
