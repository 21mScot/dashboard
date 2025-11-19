# scripts/test_scenarios_engine.py
from __future__ import annotations

from typing import List

from src.config import settings
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import run_scenario
from src.core.scenario_models import AnnualBaseEconomics, ScenarioResult


def build_simple_base_years(project_years: int) -> List[AnnualBaseEconomics]:
    """
    Minimal dummy annual economics for testing.

    This does NOT need to match your final engine – it’s just here to
    confirm that the scenario engine + settings wiring is correct.
    """

    base_price_usd = settings.DEFAULT_BTC_PRICE_USD
    usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    years: List[AnnualBaseEconomics] = []

    for year_idx in range(1, project_years + 1):
        btc_mined = 0.5  # constant, just for testing

        revenue_gbp = btc_mined * base_price_usd * usd_to_gbp
        electricity_cost_gbp = 10_000.0
        other_opex_gbp = 5_000.0

        total_opex_gbp = electricity_cost_gbp + other_opex_gbp
        ebitda_gbp = revenue_gbp - total_opex_gbp
        ebitda_margin = ebitda_gbp / revenue_gbp if revenue_gbp > 0 else 0.0

        years.append(
            AnnualBaseEconomics(
                year_index=year_idx,
                btc_mined=btc_mined,
                btc_price_usd=base_price_usd,
                revenue_gbp=revenue_gbp,
                electricity_cost_gbp=electricity_cost_gbp,
                other_opex_gbp=other_opex_gbp,
                total_opex_gbp=total_opex_gbp,
                ebitda_gbp=ebitda_gbp,
                ebitda_margin=ebitda_margin,
            )
        )

    return years


def main() -> None:
    project_years = 4
    total_capex_gbp = 200_000.0

    base_years = build_simple_base_years(project_years)

    # Use the same default client share as the UI
    scenarios_cfg = build_default_scenarios(
        client_share_override=settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE
    )

    base_cfg = scenarios_cfg["base"]

    result: ScenarioResult = run_scenario(
        name="Base case (smoke test)",
        base_years=base_years,
        cfg=base_cfg,
        total_capex_gbp=total_capex_gbp,
    )

    print("=== Scenario engine smoke test ===")
    print(f"Years: {len(result.years)}")
    print(f"Total BTC: {result.total_btc:,.3f}")
    print(f"Total revenue (£): {result.total_revenue_gbp:,.0f}")
    print(f"Total opex (£): {result.total_opex_gbp:,.0f}")
    print(f"Total client revenue (£): {result.total_client_revenue_gbp:,.0f}")
    print(f"Total 21mScot revenue (£): {result.total_operator_revenue_gbp:,.0f}")
    print(f"Total client tax (£): {result.total_client_tax_gbp:,.0f}")
    print(f"Total client net income (£): {result.total_client_net_income_gbp:,.0f}")
    print(f"Avg EBITDA margin (%): {result.avg_ebitda_margin * 100:,.1f}")


if __name__ == "__main__":
    main()
