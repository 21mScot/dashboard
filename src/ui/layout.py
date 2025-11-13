# src/ui/layout.py

from __future__ import annotations

import textwrap
from dataclasses import asdict
from datetime import datetime, timezone

import streamlit as st

from src.config import settings
from src.config.settings import LIVE_DATA_CACHE_TTL_S
from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.core.site_metrics import compute_site_metrics
from src.ui.miner_selection import render_miner_selection
from src.ui.scenarios import render_scenarios_and_risk
from src.ui.site_inputs import render_site_inputs


@st.cache_data(
    ttl=LIVE_DATA_CACHE_TTL_S,
    show_spinner="Loading live BTC network data...",
)
def load_live_network_data() -> NetworkData | None:
    """
    Try to fetch live BTC price + difficulty on every run.
    If it fails, show a structured warning and fall back to static assumptions.

    Note: get_live_network_data() is cached (TTL in settings.LIVE_DATA_TTL_HOURS),
    so this will not hammer external APIs on every UI interaction.
    """
    static_price = settings.DEFAULT_BTC_PRICE_USD
    static_diff = settings.DEFAULT_NETWORK_DIFFICULTY
    static_subsidy = settings.DEFAULT_BLOCK_SUBSIDY_BTC

    try:
        return get_live_network_data()
    except LiveDataError as e:
        warning_md = textwrap.dedent(
            "**Could not load live BTC network data — "
            "using static assumptions instead.**\n\n"
            "**Fallback values now in use:**\n"
            f"- BTC price (USD): `${static_price:,.0f}`\n"
            f"- Difficulty: `{static_diff:,}`\n"
            f"- Block subsidy: `{static_subsidy} BTC`\n"
            "\n"
            "<details>\n"
            "<summary><strong>Technical details</strong></summary>\n\n"
            "```text\n"
            f"{e}\n"
            "```\n"
            "</details>\n"
        )

        st.warning(warning_md, icon="⚠️")

        return NetworkData(
            btc_price_usd=static_price,
            difficulty=static_diff,
            block_subsidy_btc=static_subsidy,
            block_height=None,
        )

    except Exception as e:
        st.error(f"Unexpected error while loading network data: {e}")
        return None


def render_dashboard() -> None:
    """Top-level layout for the Bitcoin Mining ROI dashboard."""
    st.title("Bitcoin Mining Feasibility Dashboard")
    st.caption("Exploring site physics, BTC production, and revenue scenarios.")

    # Sidebar: allow switching live data ON/OFF
    use_live = st.sidebar.toggle("Use live BTC network data", value=True)

    network_data: NetworkData | None = load_live_network_data() if use_live else None

    # Sidebar: show live data or fallback
    if network_data is not None:
        last_updated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with st.sidebar.expander("Live BTC network data", expanded=True):
            st.metric("BTC price (USD)", f"${network_data.btc_price_usd:,.0f}")
            st.metric("Block subsidy", f"{network_data.block_subsidy_btc} BTC")
            st.caption(
                "Network difficulty is used under the hood to derive BTC/day "
                "and revenue, but is not shown directly to keep the UI "
                "client-friendly."
            )
            st.caption(f"Last updated: {last_updated_utc}")
    else:
        st.sidebar.info(
            "Using static default BTC price and difficulty "
            "(live data not available)."
        )

    # -------------------------------------------------------------------------
    # TABS
    # -------------------------------------------------------------------------
    tab_overview, tab_scenarios, tab_assumptions = st.tabs(
        [
            "📊 Overview",
            "🎯 Scenarios & Risk",
            "📋 Assumptions & Methodology",
        ]
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
            selected_miner = render_miner_selection(network_data=network_data)

        metrics = compute_site_metrics(site_inputs, selected_miner)

        st.markdown("---")
        st.markdown("## From one miner to your whole site")

        col_a, col_b, col_c = st.columns(3)
        col_a.metric(
            "ASICs supported",
            f"{metrics.asics_supported}",
            help="Number of miners that fit within the site's power budget.",
        )
        col_b.metric("Power per ASIC", f"{metrics.asic_power_kw:.2f} kW")
        col_c.metric(
            "Site power used",
            f"{metrics.site_power_used_kw:.1f} / {metrics.site_power_kw:.1f} kW",
        )

        st.caption(
            f"Approx. {metrics.site_power_spare_kw:.1f} kW spare capacity remains "
            "for future expansion or overheads."
        )

        with st.expander("🔍 Debug: raw input & derived data", expanded=False):
            st.markdown("**Site inputs**")
            st.json(asdict(site_inputs))

            st.markdown("**Selected miner**")
            st.json(asdict(selected_miner))

            st.markdown("**Derived site metrics**")
            st.json(asdict(metrics))

    # -------------------------------------------------------------------------
    # SCENARIOS & RISK TAB
    # -------------------------------------------------------------------------
    with tab_scenarios:
        render_scenarios_and_risk(
            site=site_inputs,
            miner=selected_miner,
            network_data=network_data,
        )

    # -------------------------------------------------------------------------
    # ASSUMPTIONS & METHODOLOGY TAB
    # -------------------------------------------------------------------------
    with tab_assumptions:
        st.subheader("📋 Assumptions & Methodology")
        st.info("Document data sources, formulas, and limitations here.")
