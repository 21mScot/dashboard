# src/ui/scenarios_adapter.py
from __future__ import annotations

from typing import List

from src.core.scenario_models import AnnualBaseEconomics
from src.core.scenarios_period import ScenarioAnnualEconomics


def scenario_annual_to_base_economics(
    econ: ScenarioAnnualEconomics,
) -> List[AnnualBaseEconomics]:
    """
    Adapt the original ScenarioAnnualEconomics structure into the
    AnnualBaseEconomics objects expected by the new scenario engine.

    Note: we treat `btc_price_fiat` and all *_fiat values as already
    being in GBP (or whatever your reporting currency is). To keep
    units consistent, we'll later call `run_scenario(..., usd_to_gbp=1.0)`
    so the engine does not convert again.
    """

    base_years: List[AnnualBaseEconomics] = []

    for row in econ.years:
        base_years.append(
            AnnualBaseEconomics(
                year_index=row.year_index,
                btc_mined=row.btc_mined,
                # We keep the name `btc_price_usd` in the engine, but here it
                # will actually hold your fiat (GBP) price. That's fine as
                # long as we pass usd_to_gbp=1.0 when running scenarios.
                btc_price_usd=row.btc_price_fiat,
                revenue_gbp=row.revenue_fiat,
                electricity_cost_gbp=row.electricity_cost_fiat,
                other_opex_gbp=row.other_opex_fiat,
                total_opex_gbp=row.total_opex_fiat,
                ebitda_gbp=row.ebitda_fiat,
                ebitda_margin=row.ebitda_margin,  # already a fraction 0–1
            )
        )

    return base_years
