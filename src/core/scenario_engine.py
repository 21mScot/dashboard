# src/core/scenario_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.config import settings
from src.core.site_metrics import SiteMetrics

# ----------------------------------------------------------------------
# Base annual economics (pre-scenario)
# ----------------------------------------------------------------------


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


# ----------------------------------------------------------------------
# Scenario config
# ----------------------------------------------------------------------


@dataclass
class ScenarioConfig:
    """
    Configuration parameters for a scenario.

    All percentage fields are expressed as fractions, e.g.
      +20% = 0.20, -10% = -0.10
    """

    name: str

    # Shocks relative to base assumptions
    price_pct: float  # +0.20 = +20% BTC price
    difficulty_pct: float  # +0.20 = +20% harder network
    electricity_pct: float  # +0.20 = +20% electricity cost

    # Revenue share going to the client (AD operator).
    # The remaining share (1 - client_revenue_share) goes to 21mScot.
    client_revenue_share: float  # 0.90 = 90% of BTC revenue to client


# ----------------------------------------------------------------------
# Scenario result structures
# ----------------------------------------------------------------------


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


# ----------------------------------------------------------------------
# Helper: build base annual economics from SiteMetrics
# ----------------------------------------------------------------------


def build_base_annual_from_site_metrics(
    site: SiteMetrics,
    project_years: int,
) -> List[AnnualBaseEconomics]:
    """
    Build a base-case annual economics series directly from the
    current SiteMetrics snapshot.

    Assumptions:
      - SiteMetrics already includes uptime and cooling/overhead effects.
      - BTC price is implied from site_revenue_usd_per_day / site_btc_per_day.
      - Each year in the *base* case is identical; price/difficulty/
        electricity shocks are applied later via ScenarioConfig.
    """

    if project_years <= 0:
        return []

    # If the site can't support any ASICs or produces no BTC, bail early.
    if site.asics_supported <= 0 or site.site_btc_per_day <= 0:
        return []

    # Implied BTC price in USD from site metrics
    if site.site_btc_per_day > 0:
        btc_price_usd = site.site_revenue_usd_per_day / site.site_btc_per_day
    else:
        btc_price_usd = settings.DEFAULT_BTC_PRICE_USD

    years: List[AnnualBaseEconomics] = []

    for year_idx in range(1, project_years + 1):
        # Base physics: same each year before scenario shocks
        btc_mined = site.site_btc_per_day * 365.0

        revenue_gbp = site.site_revenue_gbp_per_day * 365.0
        electricity_cost_gbp = site.site_power_cost_gbp_per_day * 365.0

        # At the moment we don't model "other opex" explicitly at the
        # site level, so keep it at zero for transparency.
        other_opex_gbp = 0.0

        total_opex_gbp = electricity_cost_gbp + other_opex_gbp
        ebitda_gbp = revenue_gbp - total_opex_gbp
        ebitda_margin = ebitda_gbp / revenue_gbp if revenue_gbp > 0 else 0.0

        years.append(
            AnnualBaseEconomics(
                year_index=year_idx,
                btc_mined=btc_mined,
                btc_price_usd=btc_price_usd,
                revenue_gbp=revenue_gbp,
                electricity_cost_gbp=electricity_cost_gbp,
                other_opex_gbp=other_opex_gbp,
                total_opex_gbp=total_opex_gbp,
                ebitda_gbp=ebitda_gbp,
                ebitda_margin=ebitda_margin,
            )
        )

    return years


# ----------------------------------------------------------------------
# Core scenario engine
# ----------------------------------------------------------------------


def _apply_scenario_to_year(
    base: AnnualBaseEconomics,
    cfg: ScenarioConfig,
    usd_to_gbp: float,
) -> AnnualScenarioEconomics:
    """
    Apply price/difficulty/electricity shocks and revenue share to a single year.
    """

    # Difficulty shock: treat difficulty_pct as relative change, where
    # +20% difficulty -> 20% less BTC, -10% difficulty -> 10% more BTC.
    btc_factor = 1.0 - cfg.difficulty_pct
    btc_mined = max(base.btc_mined * btc_factor, 0.0)

    # Price shock: adjust BTC price, then revenue based on BTC mined.
    price_factor = 1.0 + cfg.price_pct
    btc_price_usd = base.btc_price_usd * price_factor

    # Revenue in GBP from BTC * price * FX
    revenue_gbp = btc_mined * btc_price_usd * usd_to_gbp

    # Electricity cost shock
    electricity_factor = 1.0 + cfg.electricity_pct
    electricity_cost_gbp = base.electricity_cost_gbp * electricity_factor

    # For now, keep other opex unchanged
    other_opex_gbp = base.other_opex_gbp

    total_opex_gbp = electricity_cost_gbp + other_opex_gbp
    ebitda_gbp = revenue_gbp - total_opex_gbp
    ebitda_margin = ebitda_gbp / revenue_gbp if revenue_gbp > 0 else 0.0

    # Revenue split
    client_share = cfg.client_revenue_share
    client_revenue_gbp = revenue_gbp * client_share
    operator_revenue_gbp = revenue_gbp - client_revenue_gbp

    # Client-side tax and net income
    client_opex_gbp = total_opex_gbp
    profit_before_tax = client_revenue_gbp - client_opex_gbp

    tax_rate = settings.CLIENT_CORPORATION_TAX_RATE
    taxable_profit = max(profit_before_tax, 0.0)
    client_tax_gbp = taxable_profit * tax_rate

    client_net_income_gbp = profit_before_tax - client_tax_gbp

    return AnnualScenarioEconomics(
        year_index=base.year_index,
        btc_mined=btc_mined,
        btc_price_usd=btc_price_usd,
        revenue_gbp=revenue_gbp,
        electricity_cost_gbp=electricity_cost_gbp,
        other_opex_gbp=other_opex_gbp,
        total_opex_gbp=total_opex_gbp,
        ebitda_gbp=ebitda_gbp,
        ebitda_margin=ebitda_margin,
        client_revenue_gbp=client_revenue_gbp,
        operator_revenue_gbp=operator_revenue_gbp,
        client_tax_gbp=client_tax_gbp,
        client_net_income_gbp=client_net_income_gbp,
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
        year = _apply_scenario_to_year(base, cfg, usd_to_gbp)
        years.append(year)

    # Aggregates
    total_btc = sum(y.btc_mined for y in years)
    total_revenue_gbp = sum(y.revenue_gbp for y in years)
    total_opex_gbp = sum(y.total_opex_gbp for y in years)
    total_client_revenue_gbp = sum(y.client_revenue_gbp for y in years)
    total_operator_revenue_gbp = sum(y.operator_revenue_gbp for y in years)
    total_client_tax_gbp = sum(y.client_tax_gbp for y in years)
    total_client_net_income_gbp = sum(y.client_net_income_gbp for y in years)

    # Revenue-weighted average EBITDA margin
    if total_revenue_gbp > 0:
        weighted_margin = sum(y.ebitda_margin * y.revenue_gbp for y in years)
        avg_ebitda_margin = weighted_margin / total_revenue_gbp
    else:
        avg_ebitda_margin = 0.0

    # Investment metrics: payback and ROI (client perspective)
    if total_capex_gbp > 0:
        # Payback: years until cumulative net income >= CapEx
        cumulative = 0.0
        payback_years = float("inf")

        for y in years:
            prev_cum = cumulative
            cumulative += y.client_net_income_gbp
            if cumulative >= total_capex_gbp:
                # interpolate within the year
                income_this_year = y.client_net_income_gbp
                if income_this_year > 0:
                    remaining = total_capex_gbp - prev_cum
                    fraction_of_year = remaining / income_this_year
                    payback_years = (y.year_index - 1) + fraction_of_year
                break

        client_roi_multiple = total_client_net_income_gbp / total_capex_gbp
    else:
        payback_years = float("inf")
        client_roi_multiple = 0.0

    result_cfg = ScenarioConfig(
        name=name,
        price_pct=cfg.price_pct,
        difficulty_pct=cfg.difficulty_pct,
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
