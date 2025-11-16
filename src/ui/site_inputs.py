#  src/ui/site_inputs.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st


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

    # Commercial model
    commercial_model: str
    capex_client_pct: int  # implied by the chosen model


def render_site_inputs() -> SiteInputs:
    """Render the user inputs for the site-level configuration.

    Returns
    -------
    SiteInputs
        Object containing power, tariffs, project dates, and commercial model.
    """

    st.subheader("1. Setup your site parameters")
    st.markdown(
        "Provide the basic information about your mining site. "
        "These settings are used to estimate capacity, revenue, costs and "
        "project-level financials."
    )

    # ----------------------------------------------------------------------
    # Site capacity & operating costs  (⬆️ moved to the top)
    # ----------------------------------------------------------------------
    st.subheader("Site Capacity & Operating Costs")

    col1, col2 = st.columns(2)

    with col1:
        site_power_kw = st.number_input(
            "Available site power (kW)",
            min_value=1,
            max_value=5000,
            value=100,
            step=1,
            format="%d",
            help="Total electrical capacity available for miners.",
        )
        uptime_pct = st.slider(
            "Expected uptime (%)",
            min_value=80,
            max_value=100,
            value=98,
            help="Percentage of time the site is expected to remain online.",
        )

    with col2:
        electricity_cost = st.number_input(
            "Electricity cost (£ per kWh)",
            min_value=0.001,
            max_value=1.000,
            value=0.045,
            step=0.001,
            format="%.3f",
            help="Your electricity tariff, including any standing charges.",
        )

        cooling_overhead_pct = st.slider(
            "Cooling + overhead (%)",
            min_value=0,
            max_value=20,
            value=2,
            help="Additional overhead as a percentage of miner consumption.",
        )

    st.divider()

    # ----------------------------------------------------------------------
    # Project timeline  (⬇️ now below capacity)
    # ----------------------------------------------------------------------
    st.subheader("Project Timeline")

    go_live_date = st.date_input(
        "Intended go-live date",
        value=date.today(),
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
        help="How long you expect this site to run after the intended go-live date.",
    )

    project_end_date = _add_years_safe(go_live_date, project_years)

    st.caption(
        f"**Project window:** {go_live_date:%d %b %Y} → {project_end_date:%d %b %Y}"
    )

    st.divider()

    # ----------------------------------------------------------------------
    # Commercial model (client-facing)
    # ----------------------------------------------------------------------
    st.subheader("Commercial Model")

    commercial_model = st.radio(
        "Select your preferred commercial model",
        [
            "Client-owned hardware",
            "Operator-owned hardware",
            "Hybrid partnership (shared ownership)",
        ],
        help=(
            "This determines how hardware costs and revenue are shared between "
            "you and the operator."
        ),
    )

    if commercial_model == "Hybrid partnership (shared ownership)":
        capex_client_pct = st.slider(
            "Client share of hardware cost (%)",
            min_value=0,
            max_value=100,
            value=50,
            help=(
                "Percentage of the mining hardware purchased by the client. "
                "Revenue share will typically follow this split."
            ),
        )
    elif commercial_model == "Client-owned hardware":
        capex_client_pct = 100
    else:
        # Operator-owned hardware
        capex_client_pct = 0

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
        commercial_model=commercial_model,
        capex_client_pct=capex_client_pct,
    )

    return site_inputs
