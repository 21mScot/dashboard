from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from src.core.site_metrics import compute_site_metrics
from src.ui.miner_selection import render_miner_selection
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
            site_inputs = render_site_inputs()

        with right:
            selected_miner = render_miner_selection()

        # -----------------------------------------------------------------
        # From one ASIC to the whole site
        # -----------------------------------------------------------------
        metrics = compute_site_metrics(site_inputs, selected_miner)

        st.markdown("---")
        st.markdown("## From one miner to your whole site")

        col_a, col_b, col_c = st.columns(3)

        col_a.metric(
            "ASICs supported",
            f"{metrics.asics_supported}",
            help="Number of miners that fit within the site's power budget.",
        )
        col_b.metric(
            "Power per ASIC",
            f"{metrics.asic_power_kw:.2f} kW",
        )
        col_c.metric(
            "Site power used",
            f"{metrics.site_power_used_kw:.1f} / {metrics.site_power_kw:.1f} kW",
        )

        st.caption(
            f"Approx. {metrics.site_power_spare_kw:.1f} kW spare capacity "
            "remains for future expansion or overheads."
        )

        # BTC/day placeholders – ready to be wired to SEC backend
        st.markdown("### BTC production (to be wired to SEC backend)")
        st.info(
            "Per-ASIC and per-site BTC/day will be populated once this dashboard is "
            "connected to the Site Economy Calculator (SEC) backend. For now, "
            "we're focusing on the site physics (how many miners fit, and power usage)."
        )
        # BTC/day placeholders – ready to be wired to SEC backend
        st.markdown("### BTC production (to be wired to SEC backend)")
        st.info(
            "Per-ASIC and per-site BTC/day will be populated once this dashboard is "
            "connected to the Site Economy Calculator (SEC) backend. For now, "
            "we're focusing on the site physics (how many miners fit, and power usage)."
        )

        # -----------------------------------------------------------------
        # Debug: raw objects (for development + walkthroughs)
        # -----------------------------------------------------------------
        with st.expander("🔍 Debug: raw input & derived data", expanded=False):
            st.markdown("**Site inputs**")
            st.json(asdict(site_inputs))

            st.markdown("**Selected miner**")
            # MinerOption is also a dataclass, so asdict works here too
            st.json(asdict(selected_miner))

            st.markdown("**Derived site metrics**")
            st.json(asdict(metrics))

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
