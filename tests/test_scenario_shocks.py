import pytest

from src.core.scenario_calculations import (
    apply_scenario_to_year,
    btc_multiplier_from_difficulty_level_shock,
)
from src.core.scenario_models import AnnualBaseEconomics, ScenarioConfig


def test_difficulty_shock_multiplier_harder():
    assert btc_multiplier_from_difficulty_level_shock(0.20) == pytest.approx(1 / 1.20)


def test_difficulty_shock_multiplier_easier():
    assert btc_multiplier_from_difficulty_level_shock(-0.10) == pytest.approx(1 / 0.90)


def test_difficulty_shock_guardrail():
    with pytest.raises(ValueError):
        btc_multiplier_from_difficulty_level_shock(-1.0)


def test_best_base_worst_btc_ordering():
    base = AnnualBaseEconomics(
        year_index=1,
        btc_mined=100.0,
        btc_price_usd=50000.0,
        revenue_gbp=0.0,
        electricity_cost_gbp=0.0,
        other_opex_gbp=0.0,
        total_opex_gbp=0.0,
        ebitda_gbp=0.0,
        ebitda_margin=0.0,
    )
    cfg_base = ScenarioConfig(
        name="base",
        price_pct=0.0,
        difficulty_level_shock_pct=0.0,
        electricity_pct=0.0,
        client_revenue_share=1.0,
    )
    cfg_best = ScenarioConfig(
        name="best",
        price_pct=0.0,
        difficulty_level_shock_pct=-10.0,
        electricity_pct=0.0,
        client_revenue_share=1.0,
    )
    cfg_worst = ScenarioConfig(
        name="worst",
        price_pct=0.0,
        difficulty_level_shock_pct=20.0,
        electricity_pct=0.0,
        client_revenue_share=1.0,
    )

    year_base = apply_scenario_to_year(base, cfg_base, usd_to_gbp=1.0)
    year_best = apply_scenario_to_year(base, cfg_best, usd_to_gbp=1.0)
    year_worst = apply_scenario_to_year(base, cfg_worst, usd_to_gbp=1.0)

    assert year_best.btc_mined > year_base.btc_mined > year_worst.btc_mined
