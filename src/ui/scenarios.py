#  src/ui/scenarios.py
from __future__ import annotations

from typing import List, Optional

import streamlit as st

from src.config import settings
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import (
    AnnualBaseEconomics,
    ScenarioResult,
    build_base_annual_from_site_metrics,
    run_scenario,
)
from src.core.site_metrics import SiteMetrics
from src.ui.scenarios_tab import render_scenarios_tab


def _build_dummy_base_years(project_years: int) -> List[AnnualBaseEconomics]:
    """
    Legacy helper to create simple, deterministic annual economics
    so that the scenario engine and UI can be exercised even when
    no real SiteMetrics are available.

    Once you're confident with the live wiring you can delete this.
    """

    base_price_usd = settings.DEFAULT_BTC_PRICE_USD
    usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    years: List[AnnualBaseEconomics] = []

    for year_idx in range(1, project_years + 1):
        # Simple assumptions for now:
        btc_mined = max(0.5 - 0.05 * (year_idx - 1), 0.0)

        revenue_gbp = btc_mined * base_price_usd * usd_to_gbp

        electricity_cost_gbp = revenue_gbp * 0.15
        other_opex_gbp = revenue_gbp * 0.05

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


def render_scenarios_page(
    site: Optional[object] = None,
) -> None:
    """
    Top-level renderer for the '3. Scenarios & risk' tab.

    If a SiteMetrics object is provided (from layout.py), we use it to
    build real base-case annual economics. If not, we fall back to a
    simple dummy series so the tab still renders.
    """

    st.header("3. Scenarios & risk")

    controls_col1, controls_col2, controls_col3 = st.columns(3)

    with controls_col1:
        project_years = st.number_input(
            "Project duration (years)",
            min_value=1,
            max_value=30,
            value=settings.SCENARIO_FALLBACK_PROJECT_YEARS,
            step=1,
        )

    with controls_col2:
        total_capex_gbp = st.number_input(
            "Total project CapEx (£)",
            min_value=0.0,
            value=1_000_000.0,
            step=50_000.0,
            format="%.0f",
        )

    with controls_col3:
        client_share_pct = st.slider(
            "Client share of BTC revenue (%)",
            min_value=50,
            max_value=100,
            value=int(settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE * 100),
            step=1,
        )
    client_share_fraction = client_share_pct / 100.0

    # ------------------------------------------------------------------
    # Build base annual economics
    # ------------------------------------------------------------------
    if isinstance(site, SiteMetrics) and site.asics_supported > 0:
        base_years = build_base_annual_from_site_metrics(
            site=site,
            project_years=int(project_years),
        )
    else:
        # If we don't yet have real site metrics, keep the dummy series.
        base_years = _build_dummy_base_years(int(project_years))

    # If for some reason we still have no data, short-circuit gracefully.
    if not base_years:
        st.info(
            "No ASICs are currently supported by the site configuration, "
            "so project-level economics cannot be calculated."
        )
        return

    scenarios_cfg = build_default_scenarios(client_share_override=client_share_fraction)

    base_result: ScenarioResult = run_scenario(
        name="Base case",
        base_years=base_years,
        cfg=scenarios_cfg["base"],
        total_capex_gbp=total_capex_gbp,
    )
    best_result: ScenarioResult = run_scenario(
        name="Best case",
        base_years=base_years,
        cfg=scenarios_cfg["best"],
        total_capex_gbp=total_capex_gbp,
    )
    worst_result: ScenarioResult = run_scenario(
        name="Worst case",
        base_years=base_years,
        cfg=scenarios_cfg["worst"],
        total_capex_gbp=total_capex_gbp,
    )

    render_scenarios_tab(
        base_result=base_result,
        best_result=best_result,
        worst_result=worst_result,
    )


# ---------------------------------------------------------------------------
# Backwards-compatible alias for existing layout.py imports
# ---------------------------------------------------------------------------


def render_scenarios_and_risk(
    site: Optional[object] = None,
    **kwargs,
) -> None:
    """
    Backwards-compatible wrapper so that existing code that imports
    `render_scenarios_and_risk` continues to work.

    layout.py currently calls this with `site=...` which is a SiteInputs
    object, not a SiteMetrics. We accept any object here and let
    render_scenarios_page decide whether it can use it directly; if not,
    we fall back to dummy economics for now.
    """
    render_scenarios_page(site=site)
