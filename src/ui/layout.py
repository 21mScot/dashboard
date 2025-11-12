# src/ui/layout.py
from __future__ import annotations

import streamlit as st

from src.ui.site_inputs import render_site_inputs


def render_dashboard() -> None:
    """Top-level layout for the Bitcoin Mining ROI dashboard."""
    st.title("Bitcoin Mining Feasibility Dashboard")
    st.caption("Exploring site physics, BTC production, and revenue scenarios.")

    tab_overview, tab_scenarios, tab_assumptions = st.tabs(
        ["Overview", "Scenarios & Risk", "Assumptions & Methodology"]
    )

    # -------------------------------------------------------------------------
    # OVERVIEW TAB
    # -------------------------------------------------------------------------
    with tab_overview:
        st.subheader("Headline metrics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Break-even", "—", "months")
        col2.metric("Total BTC", "—", "")
        col3.metric("ROI", "—", "x")
        col4.metric("ASICs", "—", "units")

        st.markdown("---")
        st.markdown("## Site setup & miner selection")

        left, right = st.columns(2)

        with left:
            # 1. Your site setup
            _site_inputs = render_site_inputs()
            # TEMP: show values for debugging – you can remove this later
            # st.json(asdict(_site_inputs))

        with right:
            # 2. Miner selection (placeholder for a future feature/branch)
            st.markdown("### 2. Miner selection")
            st.info(
                "Miner selection UI will go here on a future branch "
                "(choose ASIC model, show specs, etc.)."
            )

    # -------------------------------------------------------------------------
    # SCENARIOS & RISK TAB
    # -------------------------------------------------------------------------
    with tab_scenarios:
        st.subheader("Scenarios & Risk")
        st.info("Future BTC price and difficulty scenarios will be shown here.")

    # -------------------------------------------------------------------------
    # ASSUMPTIONS & METHODOLOGY TAB
    # -------------------------------------------------------------------------
    with tab_assumptions:
        st.subheader("Assumptions & Methodology")
        st.info("Document data sources, formulas, and limitations here.")
