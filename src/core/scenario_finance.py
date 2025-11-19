# src/core/scenario_finance.py
from __future__ import annotations

from typing import Iterable, List, Tuple

from src.core.scenario_models import AnnualScenarioEconomics


def calculate_payback_and_roi(
    years: List[AnnualScenarioEconomics],
    total_capex_gbp: float,
    total_client_net_income_gbp: float,
) -> Tuple[float, float]:
    """
    Compute the payback period (in fractional years) and ROI multiple
    for the client given scenario results.

    Returns (payback_years, roi_multiple). Payback is infinite if CapEx
    is zero or cumulative net income never exceeds CapEx.
    """

    if total_capex_gbp <= 0:
        return float("inf"), 0.0

    cumulative = 0.0
    payback_years = float("inf")

    for year in years:
        previous = cumulative
        cumulative += year.client_net_income_gbp
        if cumulative >= total_capex_gbp:
            income_this_year = year.client_net_income_gbp
            if income_this_year > 0:
                remaining = total_capex_gbp - previous
                fraction_of_year = remaining / income_this_year
                payback_years = (year.year_index - 1) + fraction_of_year
            break

    roi_multiple = total_client_net_income_gbp / total_capex_gbp
    return payback_years, roi_multiple


def calculate_revenue_weighted_ebitda_margin(
    years: Iterable[AnnualScenarioEconomics],
) -> float:
    """
    Compute revenue-weighted average EBITDA margin for a scenario result.
    """

    years_list = list(years)
    total_revenue = sum(y.revenue_gbp for y in years_list)
    if total_revenue <= 0:
        return 0.0

    weighted_margin = sum(y.ebitda_margin * y.revenue_gbp for y in years_list)
    return weighted_margin / total_revenue
