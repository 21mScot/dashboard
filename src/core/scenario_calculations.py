# src/core/scenario_calculations.py
from __future__ import annotations

from datetime import date
from typing import List, Optional

from src.config import settings
from src.core.scenario_models import (
    AnnualBaseEconomics,
    AnnualScenarioEconomics,
    ScenarioConfig,
)
from src.core.site_metrics import SiteMetrics


def _add_years_safe(d: date, years: int) -> date:
    """Add whole years to a date, handling leap years."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year + years)


def _block_subsidy_factor(start_date: date, year_index: int) -> float:
    """Return the halving multiplier for the given project year."""
    next_halving_tuple = getattr(settings, "NEXT_HALVING_DATE", None)
    if not next_halving_tuple or len(next_halving_tuple) != 3:
        return 1.0
    halving_date = date(*next_halving_tuple)
    interval_years = int(getattr(settings, "HALVING_INTERVAL_YEARS", 4))

    year_start = _add_years_safe(start_date, year_index - 1)
    halvings = 0
    while year_start >= halving_date:
        halvings += 1
        halving_date = _add_years_safe(halving_date, interval_years)

    return 0.5**halvings if halvings > 0 else 1.0


def _difficulty_factor(year_index: int) -> float:
    """Difficulty growth reduces BTC mined over time."""
    growth = getattr(settings, "DEFAULT_ANNUAL_DIFFICULTY_GROWTH_PCT", 0.0)
    if growth == 0:
        return 1.0
    return 1.0 / ((1.0 + growth) ** (year_index - 1))


def build_base_annual_from_site_metrics(
    site: SiteMetrics,
    project_years: int,
    go_live_date: Optional[date] = None,
) -> List[AnnualBaseEconomics]:
    """
    Build a base-case annual economics series directly from the
    current SiteMetrics snapshot.

    Assumptions:
      - SiteMetrics already includes uptime and cooling/overhead effects.
      - BTC price is implied from site_revenue_usd_per_day / site_btc_per_day.
      - Base case decays BTC mined over time via difficulty drift and
        halvings; price/electricity shocks are layered later via ScenarioConfig.
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
    start_date = go_live_date or date.today()

    for year_idx in range(1, project_years + 1):
        subsidy_factor = _block_subsidy_factor(
            start_date=start_date,
            year_index=year_idx,
        )
        difficulty_factor = _difficulty_factor(year_idx)

        btc_mined = site.site_btc_per_day * 365.0 * subsidy_factor * difficulty_factor

        revenue_gbp = (
            site.site_revenue_gbp_per_day * 365.0 * subsidy_factor * difficulty_factor
        )
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


def apply_scenario_to_year(
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
