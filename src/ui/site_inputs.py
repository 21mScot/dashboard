# src/ui/site_inputs.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import streamlit as st

from src.config import settings
from src.config.env import APP_ENV, ENV_DEV


def _add_years_safe(d: date, years: int) -> date:
    """Add years to a date, handling leap years safely."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        # Handle 29 Feb -> 28 Feb on non-leap years
        return d.replace(month=2, day=28, year=d.year + years)


@dataclass
class SiteInputs:
    """Container for site-level configuration.

    Designed for use by core.site_metrics and downstream tabs.
    """

    # Project timeline
    go_live_date: date
    project_years: int
    project_end_date: date

    # Site capacity & operating costs
    site_power_kw: float
    electricity_cost: float
    uptime_pct: int
    cooling_overhead_pct: int


def render_site_inputs() -> SiteInputs:
    """Render the user inputs for the site-level configuration.

    Returns
    -------
    SiteInputs
        Object containing power, tariffs, and project dates.
    """

    st.markdown(
        "Provide the basic information about your site. "
        "These settings are used to estimate capacity, revenue, costs and "
        "forecast financials."
    )

    col_power, col_cost = st.columns(2)
    is_dev = APP_ENV == ENV_DEV
    default_power = settings.DEV_DEFAULT_SITE_POWER_KW if is_dev else 0
    default_cost = settings.DEV_DEFAULT_POWER_PRICE_GBP_PER_KWH if is_dev else 0.0
    default_uptime = settings.DEV_DEFAULT_UPTIME_PCT if is_dev else 0

    with col_power:
        site_power_kw = st.number_input(
            "Power allocated to miners (kW)",
            min_value=0,
            max_value=5000,
            value=default_power,
            step=1,
            format="%d",
            help=(
                "Electrical power consumed by miners/IT load "
                "(most becomes recoverable heat)."
            ),
        )

    with col_cost:
        electricity_cost = st.number_input(
            "Cost of generation (£ per kWh)",
            min_value=0.0,
            max_value=1.000,
            value=default_cost,
            step=0.001,
            format="%.3f",
            help="Your electricity tariff, including any standing charges.",
        )

    uptime_pct = st.slider(
        "Expected uptime (%)",
        min_value=0,
        max_value=100,
        value=default_uptime,
        help="Percentage of time the site is expected to remain online.",
    )
    # Cooling overhead hidden from UI but retained for calculations
    cooling_overhead_pct = 0

    with st.expander("Project timeline details...", expanded=False):
        go_live_date = st.date_input(
            "Intended go-live date...current installations, six weeks from today.",
            value=date.today()
            + timedelta(weeks=settings.PROJECT_GO_LIVE_INCREMENT_WEEKS),
            help=(
                "When you expect the site to start operating. "
                "Used to calculate the project window and apply halving effects "
                "in the Scenarios & Risk tab."
            ),
        )

        project_years = st.slider(
            "Project duration (years from go-live)",
            min_value=1,
            max_value=5,
            value=4,
            help=(
                "How long you expect this site to run after the intended go-live "
                "date."
            ),
        )

        project_end_date = _add_years_safe(go_live_date, project_years)

        st.caption(
            f"**Project window:** {go_live_date:%d %b %Y} → "
            f"{project_end_date:%d %b %Y}"
        )

        # Make project duration available to other tabs (e.g. Scenarios)
        st.session_state["project_years_from_go_live"] = int(project_years)
        st.session_state["project_years"] = int(project_years)
        st.session_state["project_go_live_date"] = go_live_date

    # ----------------------------------------------------------------------
    # Build and return the SiteInputs object
    # ----------------------------------------------------------------------
    site_inputs = SiteInputs(
        go_live_date=go_live_date,
        project_years=project_years,
        project_end_date=project_end_date,
        site_power_kw=site_power_kw,
        electricity_cost=electricity_cost,
        uptime_pct=uptime_pct,
        cooling_overhead_pct=cooling_overhead_pct,
    )

    return site_inputs
