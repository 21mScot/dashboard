from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import streamlit as st


@dataclass
class SiteInputs:
    """Container for all site-level configuration."""

    site_power_kw: float
    electricity_cost_p_per_kwh: float
    start_date: date
    horizon_years: int
    uptime_pct: float


def render_site_inputs() -> SiteInputs:
    """Render the 'Your site setup' panel and return the chosen values."""
    st.markdown("### 1. Your site setup")

    site_power_kw = st.number_input(
        "Site power (kW)",
        min_value=1.0,
        value=75.0,
        step=1.0,
        help="Continuous power available for mining at this site.",
    )

    electricity_cost_p_per_kwh = st.number_input(
        "Electricity cost (p/kWh)",
        min_value=0.0,
        value=12.0,
        step=0.5,
        help="Effective all-in electricity cost in pence per kWh.",
    )

    start_date = st.date_input(
        "Go-live date",
        help="Planned start date for mining operations.",
    )

    horizon_years = st.slider(
        "Planning horizon (years)",
        min_value=1,
        max_value=10,
        value=4,
        help="How far ahead we should model BTC production and revenue.",
    )

    uptime_pct = st.slider(
        "Uptime (%)",
        min_value=50,
        max_value=100,
        value=98,
        help="Expected operational uptime, including maintenance and outages.",
    )

    return SiteInputs(
        site_power_kw=site_power_kw,
        electricity_cost_p_per_kwh=electricity_cost_p_per_kwh,
        start_date=start_date,
        horizon_years=horizon_years,
        uptime_pct=uptime_pct / 100.0,
    )
