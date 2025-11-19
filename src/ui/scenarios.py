# src/ui/scenarios.py
from __future__ import annotations

import math
from typing import List, Optional

import pandas as pd
import streamlit as st

from src.config import settings
from src.core.scenario_calculations import build_base_annual_from_site_metrics
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import run_scenario
from src.core.scenario_models import AnnualBaseEconomics, ScenarioResult
from src.core.site_metrics import SiteMetrics
from src.ui.scenario_1 import render_scenario_panel


def _build_dummy_base_years(
    project_years: int,
    usd_to_gbp: float,
) -> List[AnnualBaseEconomics]:
    """
    Legacy helper to create simple, deterministic annual economics
    so that the scenario engine and UI can be exercised even when
    no real SiteMetrics are available.

    Uses the provided usd_to_gbp FX rate so that the dummy series is
    consistent with the FX shown elsewhere in the UI.
    """

    base_price_usd = settings.DEFAULT_BTC_PRICE_USD

    years: List[AnnualBaseEconomics] = []

    for year_idx in range(1, project_years + 1):
        # Simple assumptions for now:
        btc_mined = max(0.5 - 0.05 * (year_idx - 1), 0.0)

        revenue_gbp = btc_mined * base_price_usd * usd_to_gbp

        # Dummy split of opex for the placeholder series
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


def _scenario_expander_title(label: str, result: ScenarioResult) -> str:
    """
    Build a human-friendly expander title summarising the key
    decision metrics for a scenario.

    Ordering:
      1. Net income (£)
      2. Avg EBITDA margin (%)
      3. Total BTC (project)
    """
    net_income = result.total_client_net_income_gbp
    total_btc = result.total_btc
    margin_pct = result.avg_ebitda_margin * 100.0

    return (
        f"Scenario {label} – "
        f"£{net_income:,.0f} net income · "
        f"{margin_pct:,.1f}% Avg EBITDA margin · "
        f"{total_btc:,.3f} BTC"
    )


def _derive_project_years(site: Optional[object]) -> int:
    """
    Try to derive project duration (years) from:
      1. Values stored in Streamlit session_state (set on Overview tab)
      2. Attributes on the provided `site` object
      3. Fallback constant in settings
    """

    # ---- 1. Prefer explicit values from session_state
    session_keys = [
        "project_years_from_go_live",
        "project_years",
        "project_duration_years_from_go_live",
    ]
    for key in session_keys:
        if key in st.session_state:
            try:
                years = int(st.session_state[key])
                if years > 0:
                    return years
            except (TypeError, ValueError):
                continue

    # ---- 2. Inspect attributes on the `site` object, if provided ----
    candidate_attrs = [
        "project_duration_years_from_go_live",
        "project_years_from_go_live",
        "project_duration_years",
        "project_years",
        "project_duration",
    ]

    if site is not None:
        for attr in candidate_attrs:
            value = getattr(site, attr, None)
            if value is not None:
                try:
                    years = int(value)
                    if years > 0:
                        return years
                except (TypeError, ValueError):
                    continue

        for name in dir(site):
            if name.startswith("_"):
                continue
            lower = name.lower()
            if "duration" in lower and "year" in lower:
                value = getattr(site, name, None)
                try:
                    years = int(value)
                    if years > 0:
                        return years
                except (TypeError, ValueError):
                    continue

    # ---- 3. Last resort ----
    return int(settings.SCENARIO_FALLBACK_PROJECT_YEARS)


def _format_currency(value: float) -> str:
    return f"£{value:,.0f}"


def _format_btc(value: float) -> str:
    return f"{value:,.3f} BTC"


def _format_payback(years: float) -> str:
    if years is None or math.isnan(years) or math.isinf(years):
        return "No payback in project"
    if years < 0:
        return "N/A"
    return f"{years:,.1f} years"


def _render_scenario_comparison(
    base_result: ScenarioResult,
    best_result: ScenarioResult,
    worst_result: ScenarioResult,
) -> None:
    """
    Render a compact comparison of best / base / worst scenarios
    using the key decision metrics a client will care about.
    """

    rows = []

    for label, result in [
        ("Base case", base_result),
        ("Best case", best_result),
        ("Worst case", worst_result),
    ]:
        rows.append(
            {
                "Scenario": label,
                "Client net income": _format_currency(
                    result.total_client_net_income_gbp
                ),
                "Payback period": _format_payback(result.client_payback_years),
                "Total BTC (project)": _format_btc(result.total_btc),
            }
        )

    df = pd.DataFrame(rows)

    st.markdown("### Scenario comparison (headline metrics)")
    st.dataframe(df, width="content", hide_index=True)


def render_scenarios_page(
    site: Optional[object] = None,
    usd_to_gbp: float | None = None,
) -> None:
    """
    Top-level renderer for the '3. Scenarios & risks' tab.
    """

    # Ensure we always have an FX rate
    if usd_to_gbp is None:
        usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    # Main tab heading
    st.header("3. Scenarios & risks")

    # ------------------------------------------------------------------
    # Client revenue share control (full-width slider)
    # ------------------------------------------------------------------
    project_years = _derive_project_years(site)

    client_share_pct = st.slider(
        "Your share of BTC revenue (%)",
        min_value=0,
        max_value=100,
        value=int(settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE * 100),
        step=1,
    )

    client_share_fraction = client_share_pct / 100.0
    operator_share_pct = 100 - client_share_pct

    st.caption(
        f"You keep {client_share_pct:.0f}% of the gross BTC revenue - "
        f"the remainder ({operator_share_pct:.0f}%) goes to 21mScot."
    )

    # We no longer ask the user for CapEx here; we rely on model-based CapEx
    # used inside the scenario panel / CapEx breakdown. At the engine level,
    # we pass 0.0 so payback/ROI show as N/A when CapEx is not explicitly set.
    total_capex_gbp: float = 0.0

    # ------------------------------------------------------------------
    # Build base annual economics
    # ------------------------------------------------------------------
    if isinstance(site, SiteMetrics) and site.asics_supported > 0:
        base_years = build_base_annual_from_site_metrics(
            site=site,
            project_years=project_years,
        )
    else:
        base_years = _build_dummy_base_years(
            project_years=project_years,
            usd_to_gbp=usd_to_gbp,
        )

    if not base_years:
        st.info(
            "No ASICs are currently supported by the site configuration, "
            "so project-level economics cannot be calculated."
        )
        return

    # ------------------------------------------------------------------
    # Run scenarios (base / best / worst)
    # ------------------------------------------------------------------
    scenarios_cfg = build_default_scenarios(
        client_share_override=client_share_fraction,
    )

    base_result: ScenarioResult = run_scenario(
        name="Base case",
        base_years=base_years,
        cfg=scenarios_cfg["base"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )
    best_result: ScenarioResult = run_scenario(
        name="Best case",
        base_years=base_years,
        cfg=scenarios_cfg["best"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )
    worst_result: ScenarioResult = run_scenario(
        name="Worst case",
        base_years=base_years,
        cfg=scenarios_cfg["worst"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )

    # ------------------------------------------------------------------
    # Scenario comparison strip (headline view)
    # ------------------------------------------------------------------
    _render_scenario_comparison(
        base_result=base_result,
        best_result=best_result,
        worst_result=worst_result,
    )

    st.markdown("---")

    # ------------------------------------------------------------------
    # Project economics view (headings + expanders)
    # ------------------------------------------------------------------
    st.markdown("### Project economics")

    # Base case
    with st.expander(
        _scenario_expander_title("base case", base_result),
        expanded=True,
    ):
        render_scenario_panel(base_result)

    # Best case
    with st.expander(
        _scenario_expander_title("best case", best_result),
        expanded=False,
    ):
        render_scenario_panel(best_result)

    # Worst case
    with st.expander(
        _scenario_expander_title("worst case", worst_result),
        expanded=False,
    ):
        render_scenario_panel(worst_result)


# ---------------------------------------------------------------------------
# Backwards-compatible alias for existing layout.py imports
# ---------------------------------------------------------------------------


def render_scenarios_and_risk(
    site: Optional[object] = None,
    usd_to_gbp: float | None = None,
    **kwargs,
) -> None:
    """
    Backwards-compatible wrapper so that existing code that imports
    `render_scenarios_and_risk` continues to work.
    """
    render_scenarios_page(site=site, usd_to_gbp=usd_to_gbp)
