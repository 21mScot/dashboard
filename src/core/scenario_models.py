# src/core/scenario_models.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class AnnualBaseEconomics:
    """
    Base-case annual economics for the site, before any scenario shocks.

    These values are typically built from a SiteMetrics snapshot where each
    year is identical in the base case (difficulty / price shocks are
    layered on later by the scenario engine).
    """

    year_index: int

    # Core physics
    btc_mined: float
    btc_price_usd: float

    # Economics in reporting currency (GBP)
    revenue_gbp: float
    electricity_cost_gbp: float
    other_opex_gbp: float
    total_opex_gbp: float
    ebitda_gbp: float
    ebitda_margin: float  # 0–1


@dataclass
class ScenarioConfig:
    """
    Configuration parameters for a scenario.

    Shared between the scenario config factory (base/best/worst defaults)
    and the calculation engine. All percentage fields are expressed as
    fractions, e.g. +20% = 0.20, -10% = -0.10.
    """

    name: str

    # Shocks relative to base assumptions
    price_pct: float  # +0.20 = +20% BTC price
    difficulty_pct: float  # +0.20 = +20% harder network
    electricity_pct: float  # +0.20 = +20% electricity cost

    # Revenue share going to the client (AD operator).
    # The remaining share (1 - client_revenue_share) goes to 21mScot.
    client_revenue_share: float  # 0.90 = 90% of BTC revenue to client


@dataclass
class AnnualScenarioEconomics:
    """
    Per-year economics for a given scenario after applying shocks.
    """

    year_index: int

    btc_mined: float
    btc_price_usd: float

    revenue_gbp: float
    electricity_cost_gbp: float
    other_opex_gbp: float
    total_opex_gbp: float
    ebitda_gbp: float
    ebitda_margin: float  # 0–1

    # Revenue split
    client_revenue_gbp: float
    operator_revenue_gbp: float  # 21mScot

    # Tax & net income (client side)
    client_tax_gbp: float
    client_net_income_gbp: float


@dataclass
class ScenarioResult:
    """
    Aggregate results for a single scenario across all project years.
    """

    config: ScenarioConfig
    years: List[AnnualScenarioEconomics]

    total_capex_gbp: float

    # Aggregates
    total_btc: float
    total_revenue_gbp: float
    total_opex_gbp: float
    total_client_revenue_gbp: float
    total_operator_revenue_gbp: float
    total_client_tax_gbp: float
    total_client_net_income_gbp: float
    avg_ebitda_margin: float  # 0–1

    # Simple investment metrics for the client
    client_payback_years: float  # inf if never paid back
    client_roi_multiple: float  # total net income / capex
