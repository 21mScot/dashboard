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


# ---------------------------------------------------------
# Difficulty formatter (UI-only, does NOT affect calculations)
# ---------------------------------------------------------
def format_engineering(x: float | int | str) -> str:
    """
    Convert numeric difficulty to human-friendly engineering notation:
    - trillions (T)
    - billions (B)
    - millions (M)
    Always returns a string.
    """
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "N/A"

    if x >= 1e12:
        return f"{x / 1e12:.3g} T"
    elif x >= 1e9:
        return f"{x / 1e9:.3g} B"
    elif x >= 1e6:
        return f"{x / 1e6:.3g} M"
    else:
        return f"{x:.3g}"


# ---------------------------------------------------------
# Load *effective* network data (live if possible, else static)
# This is the ONLY place the decision live vs static is made.
# ---------------------------------------------------------
@st.cache_data(
    ttl=LIVE_DATA_CACHE_TTL_S,
    show_spinner="Loading BTC network data...",
)
def load_network_data(use_live: bool) -> tuple[NetworkData, bool]:
    """
    Returns a tuple of:
      - NetworkData: the data that WILL be used everywhere in the app
      - bool:       True if live data was successfully loaded, False if static

    Single source of truth: whatever this returns is used both for
    calculations and for display.
    """
    static_price = settings.DEFAULT_BTC_PRICE_USD
    static_diff = settings.DEFAULT_NETWORK_DIFFICULTY
    static_subsidy = settings.DEFAULT_BLOCK_SUBSIDY_BTC

    # If the user has explicitly disabled live data, short-circuit to static.
    if not use_live:
        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            block_height=None,
        )
        return static_data, False

    # Otherwise, attempt to fetch live data.
    try:
        live_data = get_live_network_data()
        return live_data, True

    except LiveDataError as e:
        # Live was requested but failed: show a structured warning,
        # then fall back to static assumptions.
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

        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            block_height=None,
        )
        return static_data, False

    except Exception as e:
        # Any unexpected error: log it to the UI and fall back to static.
        st.error(f"Unexpected error while loading network data: {e}")
        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            block_height=None,
        )
        return static_data, False


# ---------------------------------------------------------
# Main dashboard layout
# ---------------------------------------------------------
def render_dashboard() -> None:
    st.title("Bitcoin Mining Feasibility Dashboard")
    st.caption("Exploring site physics, BTC production, and revenue scenarios.")

    # User intent: do they want to use live data?
    requested_live = st.sidebar.toggle("Use live BTC network data", value=True)

    # Single source of truth: effective network data for the whole app.
    network_data, is_live = load_network_data(requested_live)

    # ----------- SIDEBAR STATUS + METRICS -----------
    if is_live:
        st.sidebar.success("Using LIVE BTC network data")
    elif requested_live:
        # User asked for live, but we fell back to static.
        st.sidebar.info(
            "Using static BTC price and difficulty (live data unavailable)."
        )
    else:
        # User turned live data off.
        st.sidebar.info("Using static BTC price and difficulty (live data disabled).")

    last_updated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with st.sidebar.expander("BTC network data in use", expanded=True):
        st.metric("BTC price (USD)", f"${network_data.btc_price_usd:,.0f}")
        st.metric("Difficulty", format_engineering(network_data.difficulty))
        st.metric("Block subsidy", f"{network_data.block_subsidy_btc} BTC")
        st.metric(
            "Block height",
            (
                network_data.block_height
                if network_data.block_height is not None
                else "N/A"
            ),
        )
        st.caption(
            "These values are the ones actually used for all BTC/day and "
            "revenue calculations in the dashboard."
        )
        st.caption(f"Last updated: {last_updated_utc}")

    # ---------------------------------------------------------
    # TABS
    # ---------------------------------------------------------
    tab_overview, tab_scenarios, tab_assumptions = st.tabs(
        [
            "📊 Overview",
            "🎯 Scenarios & Risk",
            "📋 Assumptions & Methodology",
        ]
    )

    # ---------------------------------------------------------
    # OVERVIEW TAB
    # ---------------------------------------------------------
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
            # Pass the same effective network_data that we also display.
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

    # ---------------------------------------------------------
    # SCENARIOS & RISK TAB
    # ---------------------------------------------------------
    with tab_scenarios:
        render_scenarios_and_risk(
            site=site_inputs,
            miner=selected_miner,
            network_data=network_data,  # same effective data
        )

    # ---------------------------------------------------------
    # ASSUMPTIONS & METHODOLOGY TAB
    # ---------------------------------------------------------
    with tab_assumptions:
        st.subheader("📋 Assumptions & Methodology")

        st.markdown("### Network data modes")

        st.markdown(
            """
We use a single set of BTC network parameters for all calculations in this dashboard.  
Those parameters come from one of three modes:

- **Live mode**  
  - Source: external APIs (CoinGecko for BTC price, Blockchain.info for difficulty, Mempool for block height).  
  - When used: when *Use live BTC network data* is enabled **and** all live calls succeed.  
  - Effect: all BTC/day and revenue calculations use the latest network values.

- **Static mode (user-selected)**  
  - Source: fixed defaults defined in the app settings.  
  - When used: when the *Use live BTC network data* toggle is **off**.  
  - Effect: calculations are based on a stable snapshot, useful for testing and repeatable comparisons.

- **Static fallback mode (live unavailable)**  
  - Source: the same fixed defaults as static mode.  
  - When used: when the toggle is **on**, but live data cannot be loaded (e.g. no network, API error, rate limiting).  
  - Effect: the app clearly warns that live data failed and automatically falls back to the static assumptions so the dashboard remains usable.

In all three cases, the **left-hand sidebar always shows exactly the BTC price, difficulty, and block subsidy values that are actually used in the calculations.**
            """
        )

        st.markdown("### Block subsidy")

        st.markdown(
            f"""
- We currently assume a block subsidy of **{settings.DEFAULT_BLOCK_SUBSIDY_BTC} BTC** (post-2024 halving).  
- This is applied uniformly across the forecast period in this POC version.  
- Future versions may introduce a halving schedule so that long-range forecasts step down the subsidy at each halving.
            """
        )

        st.markdown("### Other modelling notes")

        st.markdown(
            """
- Network difficulty is treated as constant within each scenario.  
- Transaction fees are not yet modelled explicitly; BTC/day estimates are based on block subsidy only.  
- Electricity costs, site capacity and uptime assumptions are configurable via the **Site setup** panel.
            """
        )
