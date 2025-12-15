# src/core/scenario_engine.py
from __future__ import annotations

from typing import List

from src.config import settings
from src.core.scenario_calculations import apply_scenario_to_year
from src.core.scenario_finance import (
    calculate_payback_and_roi,
    calculate_revenue_weighted_ebitda_margin,
)
from src.core.scenario_models import (
    AnnualBaseEconomics,
    AnnualScenarioEconomics,
    ScenarioConfig,
    ScenarioResult,
)


def run_scenario(
    name: str,
    base_years: List[AnnualBaseEconomics],
    cfg: ScenarioConfig,
    total_capex_gbp: float,
    usd_to_gbp: float | None = None,
) -> ScenarioResult:
    """
    Run a scenario over the provided base-year economics.

    Parameters
    ----------
    name:
        Human-friendly label for the scenario (e.g. "Base case").
    base_years:
        List of AnnualBaseEconomics rows describing the base case.
    cfg:
        ScenarioConfig with price/difficulty/electricity shocks and
        client revenue share.
    total_capex_gbp:
        Total project CapEx (used for payback / ROI calculations).
    usd_to_gbp:
        FX rate; if None, uses settings.DEFAULT_USD_TO_GBP.
    """
    # ---- NEW: make None safe for older callers ----
    if total_capex_gbp is None:
        total_capex_gbp = 0.0

    if usd_to_gbp is None:
        usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    if not base_years:
        return ScenarioResult(
            config=cfg,
            years=[],
            total_capex_gbp=total_capex_gbp,
            total_btc=0.0,
            total_revenue_gbp=0.0,
            total_opex_gbp=0.0,
            total_client_revenue_gbp=0.0,
            total_operator_revenue_gbp=0.0,
            total_client_tax_gbp=0.0,
            total_client_net_income_gbp=0.0,
            avg_ebitda_margin=0.0,
            client_payback_years=float("inf"),
            client_roi_multiple=0.0,
        )

    years: List[AnnualScenarioEconomics] = []

    for base in base_years:
        year = apply_scenario_to_year(base, cfg, usd_to_gbp)
        years.append(year)

    # Aggregates
    total_btc = sum(y.btc_mined for y in years)
    total_revenue_gbp = sum(y.revenue_gbp for y in years)
    total_opex_gbp = sum(y.total_opex_gbp for y in years)
    total_client_revenue_gbp = sum(y.client_revenue_gbp for y in years)
    total_operator_revenue_gbp = sum(y.operator_revenue_gbp for y in years)
    total_client_tax_gbp = sum(y.client_tax_gbp for y in years)
    total_client_net_income_gbp = sum(y.client_net_income_gbp for y in years)

    avg_ebitda_margin = calculate_revenue_weighted_ebitda_margin(years)

    # Investment metrics: payback and ROI (client perspective)
    payback_years, client_roi_multiple = calculate_payback_and_roi(
        years=years,
        total_capex_gbp=total_capex_gbp,
        total_client_net_income_gbp=total_client_net_income_gbp,
    )

    result_cfg = ScenarioConfig(
        name=name,
        price_pct=cfg.price_pct,
        difficulty_level_shock_pct=cfg.difficulty_level_shock_pct,
        electricity_pct=cfg.electricity_pct,
        client_revenue_share=cfg.client_revenue_share,
    )

    return ScenarioResult(
        config=result_cfg,
        years=years,
        total_capex_gbp=total_capex_gbp,
        total_btc=total_btc,
        total_revenue_gbp=total_revenue_gbp,
        total_opex_gbp=total_opex_gbp,
        total_client_revenue_gbp=total_client_revenue_gbp,
        total_operator_revenue_gbp=total_operator_revenue_gbp,
        total_client_tax_gbp=total_client_tax_gbp,
        total_client_net_income_gbp=total_client_net_income_gbp,
        avg_ebitda_margin=avg_ebitda_margin,
        client_payback_years=payback_years,
        client_roi_multiple=client_roi_multiple,
    )
