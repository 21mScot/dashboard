import json
from datetime import date
from pathlib import Path

import pytest

from src.config import settings
from src.core.monthly_forecast import build_monthly_forecast
from src.core.site_metrics import SiteMetrics


def load_scenarios():
    path = Path(__file__).parent / "data" / "braiins_alignment_scenarios.json"
    with path.open() as f:
        return json.load(f)


@pytest.mark.parametrize("scenario", load_scenarios())
def test_btc_forecast_matches_braiins_scenarios(scenario):
    # Skip scaffolds until expected values are populated.
    expected_btc = scenario.get("expected_btc_mined")
    if expected_btc is None:
        pytest.skip(f"{scenario['name']} missing expected_btc_mined")

    site = SiteMetrics.from_calibration(
        miner_ths=scenario["miner_ths"],
        miner_kw=scenario["miner_kw"],
        start_difficulty=scenario["start_difficulty"],
        start_btc_price_usd=scenario.get("start_btc_price_usd"),
        tx_fee_btc_per_block=scenario.get("tx_fee_btc_per_block"),
        pool_fee_pct=scenario.get("pool_fee_pct", 0.0),
        uptime_pct=100.0,
        electricity_usd_per_kwh=scenario.get("electricity_usd_per_kwh", 0.0),
        additional_opex_usd_per_month=scenario.get(
            "additional_opex_usd_per_month", 0.0
        ),
        usd_to_gbp=scenario.get("usd_to_gbp"),
    )

    difficulty_growth_pct = scenario["difficulty_growth_annual_pct"]
    fee_growth_pct = scenario.get("fee_growth_annual_pct", 0.0)
    project_years = max(1, scenario["months"] // 12)
    start_date = getattr(settings, "FORECAST_START_DATE", None) or date(
        *getattr(settings, "NEXT_HALVING_DATE", (date.today().year, 1, 1))
    )

    rows = build_monthly_forecast(
        site=site,
        start_date=start_date,
        project_years=project_years,
        fee_growth_pct_per_year=float(fee_growth_pct),
        base_fee_btc_per_block=scenario["tx_fee_btc_per_block"],
        difficulty_growth_pct_per_year=difficulty_growth_pct,
    )

    total_btc = sum(r.btc_mined for r in rows)

    if expected_btc <= 0:
        pytest.skip(f"{scenario['name']} has non-positive expected_btc_mined")

    diff_pct = abs(total_btc - expected_btc) / expected_btc * 100.0

    assert diff_pct <= scenario["tolerance_pct"], (
        f"{scenario['name']} BTC mismatch: "
        f"expected {expected_btc:.8f}, got {total_btc:.8f} ({diff_pct:.2f}% diff)"
    )
