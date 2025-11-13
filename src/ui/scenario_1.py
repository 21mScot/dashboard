# src/ui/scenario_1.py

from __future__ import annotations

import streamlit as st

from src.core.scenarios_period import (
    ScenarioAnnualEconomics,
    annual_economics_to_dataframe,
)


def render_scenario_1(econ: ScenarioAnnualEconomics) -> None:
    """
    Render the Scenario 1 MVP: annual economics only.
    Assumes `econ` has already been computed (or is dummy data).
    """
    st.subheader("Scenario 1 – Annual site economics")

    st.caption(
        "Annual site-level economics based on Scenario 1 assumptions. "
        "This view excludes CapEx, revenue share, and tax effects for clarity."
    )

    # --- Top summary metrics ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total BTC (all years)",
            value=f"{econ.total_btc:,.3f}",
        )

    with col2:
        st.metric(
            label="Total revenue (£)",
            value=f"£{econ.total_revenue:,.0f}",
        )

    with col3:
        st.metric(
            label="Total OpEx (£)",
            value=f"£{econ.total_opex:,.0f}",
        )

    with col4:
        st.metric(
            label="Avg EBITDA margin",
            value=f"{econ.avg_ebitda_margin * 100:,.1f}%",
        )

    st.markdown("---")

    # --- Annual table ---
    st.markdown("#### Annual economics table")

    df = annual_economics_to_dataframe(econ)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )
