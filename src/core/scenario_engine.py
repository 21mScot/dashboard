# src/core/scenario_engine.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from src.config import settings
from src.core.capex_config import CapexTaxConfig, get_default_capex_tax_config
from src.core.scenario_config import ScenarioConfig
from src.core.site_metrics import SiteMetrics  # add near the top with other imports

# ---------------------------------------------------------------------------
# 1) Base annual inputs (what you already have from the main engine)
# ---------------------------------------------------------------------------


@dataclass
class AnnualBaseEconomics:
    """
    Mirrors the "Annual economics table" currently shown in the UI.

    This has **no scenario logic** in it – it's just the base case that
    comes from your existing physics / BTC / revenue engine.
    """

    year_index: int  # 1-based: 1, 2, 3, ...
    btc_mined: float
    btc_price_usd: float

    revenue_gbp: float
    electricity_cost_gbp: float
    other_opex_gbp: float

    total_opex_gbp: float
    ebitda_gbp: float
    ebitda_margin: float  # e.g. 0.928 for 92.8%


# ---------------------------------------------------------------------------
# 2) Client-side tax / CapEx result per year
# ---------------------------------------------------------------------------


@dataclass
class ClientTaxYear:
    year_index: int
    ebitda_gbp: float

    # Tax modelling
    capital_allowance_gbp: float
    taxable_profit_gbp: float
    tax_gbp: float
    net_income_gbp: float  # after tax

    # For transparency
    tax_rate: float
    allowance_rate: float


# ---------------------------------------------------------------------------
# 3) Scenario economics per year
# ---------------------------------------------------------------------------


@dataclass
class AnnualScenarioEconomics:
    year_index: int
    scenario_name: str

    btc_mined: float
    btc_price_usd: float

    revenue_gbp: float
    electricity_cost_gbp: float
    other_opex_gbp: float
    total_opex_gbp: float
    ebitda_gbp: float
    ebitda_margin: float

    # Revenue split
    client_revenue_gbp: float
    operator_revenue_gbp: float

    # Client tax + net income
    client_tax_gbp: float
    client_net_income_gbp: float


# ---------------------------------------------------------------------------
# 4) Roll-up for one scenario
# ---------------------------------------------------------------------------


@dataclass
class ScenarioResult:
    config: ScenarioConfig
    years: List[AnnualScenarioEconomics]

    total_btc: float
    total_revenue_gbp: float
    total_opex_gbp: float
    avg_ebitda_margin: float

    total_client_revenue_gbp: float
    total_operator_revenue_gbp: float

    total_client_tax_gbp: float
    total_client_net_income_gbp: float

    # Hooks for future (IRR, NPV)
    irr_client: float | None = None
    irr_operator: float | None = None


# ---------------------------------------------------------------------------
# 5) Core transformation functions
# ---------------------------------------------------------------------------


def _apply_difficulty_shock_to_btc(
    base_btc_mined: float,
    difficulty_pct: float,
) -> float:
    """
    Simple heuristic: if difficulty increases by +X%, our share of BTC
    goes down roughly by the same proportion.

    Example:
      difficulty_pct = +0.20 -> btc_mined / 1.20
      difficulty_pct = -0.10 -> btc_mined / 0.90
    """
    difficulty_multiplier = 1.0 + difficulty_pct
    if difficulty_multiplier <= 0:
        # Guardrail against extreme/impossible settings
        return 0.0

    return base_btc_mined / difficulty_multiplier


def apply_scenario_to_year(
    base: AnnualBaseEconomics,
    cfg: ScenarioConfig,
    usd_to_gbp: float,
) -> AnnualScenarioEconomics:
    """
    Take one row of base economics and apply:
      - price shock
      - difficulty shock
      - electricity price shock
      - revenue-sharing

    Pure function: no side-effects, no I/O.
    """

    # 1) Difficulty shock → BTC mined
    btc_mined = _apply_difficulty_shock_to_btc(
        base_btc_mined=base.btc_mined,
        difficulty_pct=cfg.difficulty_pct,
    )

    # 2) Price shock
    price_multiplier = 1.0 + cfg.price_pct
    btc_price_usd = base.btc_price_usd * price_multiplier

    # 3) Revenue (BTC × price × FX)
    revenue_gbp = btc_mined * btc_price_usd * usd_to_gbp

    # 4) Electricity cost shock
    elec_multiplier = 1.0 + cfg.electricity_pct
    electricity_cost_gbp = base.electricity_cost_gbp * elec_multiplier

    # 5) Other Opex left unchanged for simplicity / transparency
    other_opex_gbp = base.other_opex_gbp

    total_opex_gbp = electricity_cost_gbp + other_opex_gbp
    ebitda_gbp = revenue_gbp - total_opex_gbp
    ebitda_margin = ebitda_gbp / revenue_gbp if revenue_gbp > 0 else 0.0

    # 6) Revenue share split
    client_share = cfg.client_revenue_share
    operator_share = 1.0 - client_share

    client_revenue_gbp = revenue_gbp * client_share
    operator_revenue_gbp = revenue_gbp * operator_share

    return AnnualScenarioEconomics(
        year_index=base.year_index,
        scenario_name=cfg.name,
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
        client_tax_gbp=0.0,  # filled in later
        client_net_income_gbp=0.0,  # filled in later
    )


# ---------------------------------------------------------------------------
# 6) Client tax profile from EBITDA + CapEx
# ---------------------------------------------------------------------------


def compute_client_tax_profile(
    annual_ebitda: list[float],
    total_capex_gbp: float,
    cfg: CapexTaxConfig | None = None,
) -> list[ClientTaxYear]:
    """
    Given a list of annual EBITDA values for the *client* and a total CapEx
    amount, compute a simple tax profile with a first-year capital allowance.

    Approximations:
      - Uses EBITDA as a proxy for taxable profit.
      - Full first-year allowance (no carry-forward of unused pools).
      - No loss carry-forward; taxable profit is never negative.
    """

    if cfg is None:
        cfg = get_default_capex_tax_config()

    tax_rate = cfg.corporation_tax_rate
    allowance_rate = cfg.first_year_allowance_pct

    n_years = len(annual_ebitda)
    result: list[ClientTaxYear] = []

    if n_years == 0:
        return result

    # Year 1 – apply capital allowance
    allowance_y1 = total_capex_gbp * allowance_rate
    ebitda_y1 = annual_ebitda[0]

    taxable_profit_y1 = max(ebitda_y1 - allowance_y1, 0.0)
    tax_y1 = taxable_profit_y1 * tax_rate
    net_income_y1 = ebitda_y1 - tax_y1

    result.append(
        ClientTaxYear(
            year_index=1,
            ebitda_gbp=ebitda_y1,
            capital_allowance_gbp=allowance_y1,
            taxable_profit_gbp=taxable_profit_y1,
            tax_gbp=tax_y1,
            net_income_gbp=net_income_y1,
            tax_rate=tax_rate,
            allowance_rate=allowance_rate,
        )
    )

    # Years 2..N – normal corporation tax, no new allowance
    for i in range(1, n_years):
        ebitda = annual_ebitda[i]
        taxable_profit = max(ebitda, 0.0)
        tax = taxable_profit * tax_rate
        net_income = ebitda - tax

        result.append(
            ClientTaxYear(
                year_index=i + 1,
                ebitda_gbp=ebitda,
                capital_allowance_gbp=0.0,
                taxable_profit_gbp=taxable_profit,
                tax_gbp=tax,
                net_income_gbp=net_income,
                tax_rate=tax_rate,
                allowance_rate=0.0,
            )
        )

    return result


# ---------------------------------------------------------------------------
# 7) High-level scenario runner
# ---------------------------------------------------------------------------


def run_scenario(
    name: str,
    base_years: list[AnnualBaseEconomics],
    cfg: ScenarioConfig,
    total_capex_gbp: float,
    usd_to_gbp: float | None = None,
    capex_tax_cfg: CapexTaxConfig | None = None,
) -> ScenarioResult:
    """
    High-level entry point: run one scenario (base / best / worst).

    This is what the UI will call.
    """

    if usd_to_gbp is None:
        usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    # 1) Apply scenario shocks + revenue share
    scenario_years: list[AnnualScenarioEconomics] = [
        apply_scenario_to_year(base=year, cfg=cfg, usd_to_gbp=usd_to_gbp)
        for year in base_years
    ]

    # 2) Client EBITDA per year (their revenue minus all opex)
    client_ebitda_per_year = [
        y.client_revenue_gbp - y.total_opex_gbp for y in scenario_years
    ]

    # 3) Tax profile based on client EBITDA + CapEx
    tax_years = compute_client_tax_profile(
        annual_ebitda=client_ebitda_per_year,
        total_capex_gbp=total_capex_gbp,
        cfg=capex_tax_cfg,
    )
    tax_by_year = {t.year_index: t for t in tax_years}

    # 4) Merge tax back into annual scenario rows
    for y in scenario_years:
        tax_row = tax_by_year.get(y.year_index)
        if tax_row:
            y.client_tax_gbp = tax_row.tax_gbp
            y.client_net_income_gbp = tax_row.net_income_gbp

    # 5) Aggregate totals / headline metrics
    total_btc = sum(y.btc_mined for y in scenario_years)
    total_revenue_gbp = sum(y.revenue_gbp for y in scenario_years)
    total_opex_gbp = sum(y.total_opex_gbp for y in scenario_years)

    total_client_revenue_gbp = sum(y.client_revenue_gbp for y in scenario_years)
    total_operator_revenue_gbp = sum(y.operator_revenue_gbp for y in scenario_years)

    total_client_tax_gbp = sum(y.client_tax_gbp for y in scenario_years)
    total_client_net_income_gbp = sum(y.client_net_income_gbp for y in scenario_years)

    avg_ebitda_margin = (
        sum(y.ebitda_margin for y in scenario_years) / len(scenario_years)
        if scenario_years
        else 0.0
    )

    return ScenarioResult(
        config=cfg,
        years=scenario_years,
        total_btc=total_btc,
        total_revenue_gbp=total_revenue_gbp,
        total_opex_gbp=total_opex_gbp,
        avg_ebitda_margin=avg_ebitda_margin,
        total_client_revenue_gbp=total_client_revenue_gbp,
        total_operator_revenue_gbp=total_operator_revenue_gbp,
        total_client_tax_gbp=total_client_tax_gbp,
        total_client_net_income_gbp=total_client_net_income_gbp,
        irr_client=None,
        irr_operator=None,
    )


def build_base_annual_from_site_metrics(
    site: SiteMetrics,
    project_years: int,
) -> list[AnnualBaseEconomics]:
    """
    Build a base-case annual economics series directly from the
    current SiteMetrics snapshot.

    Assumptions:
      - SiteMetrics already includes uptime and cooling/overhead effects.
      - BTC price is implied from site_revenue_usd_per_day / site_btc_per_day.
      - No additional difficulty or price drift is applied here; those
        effects are modelled in the scenario engine via ScenarioConfig
        shocks (price_pct, difficulty_pct, etc.).
    """

    # If the site can't support any ASICs or produces no BTC, bail early.
    if site.asics_supported <= 0 or site.site_btc_per_day <= 0:
        return []

    # Implied BTC price in USD from site metrics (safe fallback if weird inputs).
    if site.site_btc_per_day > 0:
        btc_price_usd = site.site_revenue_usd_per_day / site.site_btc_per_day
    else:
        btc_price_usd = settings.DEFAULT_BTC_PRICE_USD

    base_years: list[AnnualBaseEconomics] = []

    for year_idx in range(1, project_years + 1):
        # For now we treat each year as identical in the base case.
        # Difficulty / price shocks are applied later by the scenario engine.
        btc_mined = site.site_btc_per_day * 365.0

        revenue_gbp = site.site_revenue_gbp_per_day * 365.0
        electricity_cost_gbp = site.site_power_cost_gbp_per_day * 365.0

        # At the moment we don't model "other opex" explicitly at the
        # site level, so keep it at zero for transparency.
        other_opex_gbp = 0.0

        total_opex_gbp = electricity_cost_gbp + other_opex_gbp
        ebitda_gbp = revenue_gbp - total_opex_gbp
        ebitda_margin = ebitda_gbp / revenue_gbp if revenue_gbp > 0 else 0.0

        base_years.append(
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

    return base_years
