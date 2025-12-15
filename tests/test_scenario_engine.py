import math
from dataclasses import replace

import pytest

from src.config import settings
from src.core.scenario_calculations import build_base_annual_from_site_metrics
from src.core.scenario_engine import run_scenario
from src.core.scenario_finance import (
    calculate_payback_and_roi,
    calculate_revenue_weighted_ebitda_margin,
)
from src.core.scenario_models import (
    AnnualScenarioEconomics,
    ScenarioConfig,
)
from src.core.site_metrics import SiteMetrics


@pytest.fixture()
def sample_site_metrics() -> SiteMetrics:
    return SiteMetrics(
        asics_supported=100,
        power_per_asic_kw=3.0,
        site_power_used_kw=300.0,
        site_power_available_kw=300.0,
        spare_capacity_kw=0.0,
        site_btc_per_day=0.4,
        site_revenue_usd_per_day=20_000.0,
        site_revenue_gbp_per_day=16_000.0,
        site_power_cost_gbp_per_day=4_000.0,
        site_net_revenue_gbp_per_day=12_000.0,
        net_revenue_per_kw_gbp_per_day=40.0,
        net_revenue_per_kwh_gbp=1.6666666666666667,
    )


def test_build_base_years_from_site_metrics(sample_site_metrics: SiteMetrics):
    base_years = build_base_annual_from_site_metrics(sample_site_metrics, 3)
    assert len(base_years) == 3

    first_year = base_years[0]
    assert first_year.year_index == 1
    assert first_year.btc_mined == pytest.approx(
        sample_site_metrics.site_btc_per_day * 365
    )

    implied_btc_price = (
        sample_site_metrics.site_revenue_usd_per_day
        / sample_site_metrics.site_btc_per_day
    )
    assert first_year.btc_price_usd == pytest.approx(implied_btc_price)

    expected_revenue_gbp = sample_site_metrics.site_revenue_gbp_per_day * 365
    expected_electricity_gbp = sample_site_metrics.site_power_cost_gbp_per_day * 365
    assert first_year.revenue_gbp == pytest.approx(expected_revenue_gbp)
    assert first_year.electricity_cost_gbp == pytest.approx(expected_electricity_gbp)
    assert first_year.total_opex_gbp == pytest.approx(expected_electricity_gbp)
    assert first_year.ebitda_gbp == pytest.approx(
        expected_revenue_gbp - expected_electricity_gbp
    )


def test_build_base_years_with_no_capacity_returns_empty(
    sample_site_metrics: SiteMetrics,
):
    site_without_capacity = replace(
        sample_site_metrics, asics_supported=0, site_btc_per_day=0.0
    )
    base_years = build_base_annual_from_site_metrics(site_without_capacity, 5)
    assert base_years == []


def test_run_scenario_applies_expected_shocks(sample_site_metrics: SiteMetrics):
    base_years = build_base_annual_from_site_metrics(sample_site_metrics, 3)
    cfg = ScenarioConfig(
        name="Client share 85%",
        price_pct=0.15,
        difficulty_level_shock_pct=10.0,
        electricity_pct=0.20,
        client_revenue_share=0.85,
    )
    capex = 5_000_000.0
    usd_to_gbp = 0.8

    result = run_scenario(
        name="Upside",
        base_years=base_years,
        cfg=cfg,
        total_capex_gbp=capex,
        usd_to_gbp=usd_to_gbp,
    )

    assert result.config.name == "Upside"
    assert len(result.years) == 3

    base = base_years[0]
    btc_per_year = base.btc_mined / 1.10
    price_usd = base.btc_price_usd * (1.0 + cfg.price_pct)
    revenue_gbp = btc_per_year * price_usd * usd_to_gbp
    electricity_gbp = base.electricity_cost_gbp * (1.0 + cfg.electricity_pct)
    client_revenue_gbp = revenue_gbp * cfg.client_revenue_share
    profit_before_tax = client_revenue_gbp - electricity_gbp
    client_tax_gbp = max(profit_before_tax, 0.0) * settings.CLIENT_CORPORATION_TAX_RATE
    client_net_income = profit_before_tax - client_tax_gbp

    years = len(base_years)
    assert result.total_btc == pytest.approx(btc_per_year * years)
    assert result.total_revenue_gbp == pytest.approx(revenue_gbp * years)
    assert result.total_opex_gbp == pytest.approx(electricity_gbp * years)
    assert result.total_client_revenue_gbp == pytest.approx(client_revenue_gbp * years)
    assert result.total_operator_revenue_gbp == pytest.approx(
        (revenue_gbp - client_revenue_gbp) * years
    )
    assert result.total_client_tax_gbp == pytest.approx(client_tax_gbp * years)
    assert result.total_client_net_income_gbp == pytest.approx(
        client_net_income * years
    )

    cumulative = 0.0
    expected_payback = float("inf")
    for idx in range(1, years + 1):
        prev = cumulative
        cumulative += client_net_income
        if cumulative >= capex:
            remaining = capex - prev
            expected_payback = (idx - 1) + remaining / client_net_income
            break

    assert result.client_payback_years == pytest.approx(expected_payback)
    assert result.client_roi_multiple == pytest.approx(
        (client_net_income * years) / capex
    )


def _make_annual_result(
    year_index: int, client_net_income: float
) -> AnnualScenarioEconomics:
    return AnnualScenarioEconomics(
        year_index=year_index,
        btc_mined=0.0,
        btc_price_usd=0.0,
        revenue_gbp=1.0,
        electricity_cost_gbp=0.5,
        other_opex_gbp=0.0,
        total_opex_gbp=0.5,
        ebitda_gbp=0.5,
        ebitda_margin=0.5,
        client_revenue_gbp=1.0,
        operator_revenue_gbp=0.0,
        client_tax_gbp=0.0,
        client_net_income_gbp=client_net_income,
    )


def test_calculate_payback_and_roi_returns_fractional_year():
    years = [
        _make_annual_result(1, 100_000.0),
        _make_annual_result(2, 200_000.0),
        _make_annual_result(3, 400_000.0),
    ]
    total_net = sum(y.client_net_income_gbp for y in years)
    payback, roi = calculate_payback_and_roi(
        years,
        total_capex_gbp=450_000.0,
        total_client_net_income_gbp=total_net,
    )

    assert payback == pytest.approx(2.375)
    assert roi == pytest.approx(total_net / 450_000.0)


def test_calculate_payback_handles_zero_capex():
    years = [_make_annual_result(1, 50_000.0)]
    payback, roi = calculate_payback_and_roi(
        years,
        total_capex_gbp=0.0,
        total_client_net_income_gbp=50_000.0,
    )
    assert math.isinf(payback)
    assert roi == 0.0


def test_calculate_revenue_weighted_margin_handles_zero_revenue():
    years = [
        _make_annual_result(1, 10_000.0),
    ]
    years[0].revenue_gbp = 0.0
    assert calculate_revenue_weighted_ebitda_margin(years) == 0.0


def test_calculate_revenue_weighted_margin_returns_weighted_average():
    years = [
        _make_annual_result(1, 0.0),
        _make_annual_result(2, 0.0),
    ]
    years[0].revenue_gbp = 100.0
    years[0].ebitda_margin = 0.10
    years[1].revenue_gbp = 300.0
    years[1].ebitda_margin = 0.40

    result = calculate_revenue_weighted_ebitda_margin(years)
    expected = (0.10 * 100 + 0.40 * 300) / 400
    assert result == pytest.approx(expected)
