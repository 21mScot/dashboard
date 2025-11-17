# src/ui/layout.py
from __future__ import annotations

import textwrap
from dataclasses import asdict
from datetime import datetime, timezone

import streamlit as st

from src.config import settings
from src.config.settings import LIVE_DATA_CACHE_TTL_S
from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.core.site_metrics import SiteMetrics, compute_site_metrics
from src.ui.assumptions import render_assumptions_and_methodology
from src.ui.miner_selection import render_miner_selection
from src.ui.scenarios import render_scenarios_and_risk
from src.ui.site_inputs import render_site_inputs


# ---------------------------------------------------------
# Difficulty formatter (UI-only)
# ---------------------------------------------------------
def format_engineering(x: float | int | str) -> str:
    """Format large numbers into engineering notation (T, B, M)."""
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
# Load effective network data (live if possible)
# ---------------------------------------------------------
@st.cache_data(
    ttl=LIVE_DATA_CACHE_TTL_S,
    show_spinner="Loading BTC network data...",
)
def load_network_data(use_live: bool) -> tuple[NetworkData, bool]:
    """
    Returns:
      - NetworkData actually used for all calculations
      - bool flag: True if live loaded successfully, else False (static)
    """
    static_price = settings.DEFAULT_BTC_PRICE_USD
    static_diff = settings.DEFAULT_NETWORK_DIFFICULTY
    static_subsidy = settings.DEFAULT_BLOCK_SUBSIDY_BTC
    static_usd_to_gbp = settings.DEFAULT_USD_TO_GBP

    # Explicitly static
    if not use_live:
        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            usd_to_gbp=float(static_usd_to_gbp),
            block_height=None,
        )
        return static_data, False

    # Try live
    try:
        live_data = get_live_network_data()
        return live_data, True

    except LiveDataError as e:
        # Live requested but failed → warn and fall back
        warning_md = textwrap.dedent(
            "**Could not load live BTC network data — "
            "using static assumptions instead.**\n\n"
            "**Fallback values now in use:**\n"
            f"- BTC price (USD): `${static_price:,.0f}`\n"
            f"- Difficulty: `{static_diff:,}`\n"
            f"- Block subsidy: `{static_subsidy} BTC`\n"
            f"- USD/GBP FX: `{static_usd_to_gbp:.3f}`\n\n"
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
            usd_to_gbp=float(static_usd_to_gbp),
            block_height=None,
        )
        return static_data, False

    except Exception as e:  # noqa: BLE001
        # Any unexpected error → log & fall back
        st.error(f"Unexpected error while loading network data: {e}")
        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            usd_to_gbp=float(static_usd_to_gbp),
            block_height=None,
        )
        return static_data, False


# ---------------------------------------------------------
# Helper: derive SiteMetrics from UI inputs
# ---------------------------------------------------------
def build_site_metrics_from_inputs(
    site_inputs,
    selected_miner,
    network_data: NetworkData,
) -> SiteMetrics:
    """
    Convenience wrapper to derive SiteMetrics from the current UI state.

    We use getattr() with a few fallback attribute names so this remains
    robust even if the SiteInputs dataclass changes slightly.
    """

    # Site power (kW)
    site_power_kw = (
        getattr(site_inputs, "available_site_power_kw", None)
        or getattr(site_inputs, "site_power_kw", None)
        or 0.0
    )

    # Electricity cost (£ / kWh)
    electricity_cost_per_kwh_gbp = (
        getattr(site_inputs, "electricity_cost_per_kwh_gbp", None)
        or getattr(site_inputs, "electricity_cost_gbp_per_kwh", None)
        or getattr(site_inputs, "electricity_cost_per_kwh", None)
        or getattr(site_inputs, "electricity_cost", None)
        or 0.0
    )

    # Uptime (%)
    uptime_pct = (
        getattr(site_inputs, "expected_uptime_pct", None)
        or getattr(site_inputs, "uptime_pct", None)
        or 0.0
    )

    # Cooling + overhead (%)
    cooling_overhead_pct = (
        getattr(site_inputs, "cooling_overhead_pct", None)
        or getattr(site_inputs, "cooling_and_overhead_pct", None)
        or getattr(site_inputs, "cooling_overhead_percent", None)
        or 0.0
    )

    return compute_site_metrics(
        miner=selected_miner,
        network=network_data,
        site_power_kw=site_power_kw,
        electricity_cost_per_kwh_gbp=electricity_cost_per_kwh_gbp,
        uptime_pct=uptime_pct,
        cooling_overhead_pct=cooling_overhead_pct,
    )


# ---------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------
def render_dashboard() -> None:
    st.title("Bitcoin Mining Feasibility Dashboard")
    st.caption("Exploring site physics, BTC production, and revenue scenarios.")

    # User intent: do they want to use live data?
    requested_live = st.sidebar.toggle(
        "Use live BTC network data",
        value=True,
        key="use_live_btc_network_data_toggle",
    )

    # Single source of truth for network data
    network_data, is_live = load_network_data(requested_live)

    # Sidebar status
    if is_live:
        st.sidebar.success("Using LIVE BTC network data")
    elif requested_live:
        st.sidebar.info("Using static BTC price and difficulty (live unavailable).")
    else:
        st.sidebar.info("Using static BTC price and difficulty (live disabled).")

    # This always shows the 'current date and time'
    # That is not necessarily when the data was last updated.
    last_updated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with st.sidebar.expander("BTC network data in use", expanded=True):
        st.metric("BTC price (USD)", f"${network_data.btc_price_usd:,.0f}")
        st.metric("Difficulty", format_engineering(network_data.difficulty))
        st.metric("Block subsidy", f"{network_data.block_subsidy_btc} BTC")
        st.metric("Block height", network_data.block_height or "N/A")
        st.caption("These values drive all BTC/day and revenue calculations.")
        st.caption(f"Last updated: {last_updated_utc}")

    with st.sidebar.expander("Foreign exchange value", expanded=True):
        st.metric("USD/GBP exchange rate", f"${network_data.usd_to_gbp:.3f}")
        st.caption("This value drives all the USD to GBP currency conversions.")
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
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Break-even", "—", "months")
        c2.metric("Total BTC", "—")
        c3.metric("ROI", "—", "x")
        c4.metric("ASICs", "—", "units")

        st.markdown("---")
        st.markdown("## Site setup & miner selection")

        # Inputs + miner selection
        left, right = st.columns(2)
        with left:
            site_inputs = render_site_inputs()
        with right:
            selected_miner = render_miner_selection(network_data=network_data)

        # Compute site metrics from the current inputs
        site_metrics = build_site_metrics_from_inputs(
            site_inputs=site_inputs,
            selected_miner=selected_miner,
            network_data=network_data,
        )

        st.markdown("---")
        st.markdown("## See your site performance")

        # Power utilisation (%)
        if site_metrics.site_power_available_kw > 0:
            power_used_pct = (
                site_metrics.site_power_used_kw
                / site_metrics.site_power_available_kw
                * 100.0
            )
        else:
            power_used_pct = 0.0

        # -----------------------------------------------------
        # ROW 1 — FINANCIALS FIRST
        # -----------------------------------------------------
        f1, f2, f3 = st.columns(3)

        with f1:
            st.metric(
                "Net revenue / day",
                f"£{site_metrics.site_net_revenue_gbp_per_day:,.0f}",
            )

        with f2:
            st.metric(
                "Site BTC / day",
                f"{site_metrics.site_btc_per_day:.5f} BTC",
            )

        with f3:
            st.metric(
                "Site revenue / day",
                f"£{site_metrics.site_revenue_gbp_per_day:,.0f} / "
                f"${site_metrics.site_revenue_usd_per_day:,.0f}",
            )

        # -----------------------------------------------------
        # ROW 2 — UTILISATION & PHYSICS
        # -----------------------------------------------------
        u1, u2, u3 = st.columns(3)

        with u1:
            st.metric(
                "Site power utilisation (%)",
                f"{power_used_pct:.1f} %",
                help=(
                    f"Using {site_metrics.site_power_used_kw:.1f} kW out of "
                    f"{site_metrics.site_power_available_kw:.1f} kW "
                    f"({power_used_pct:.1f}% of available site capacity)."
                ),
            )

        with u2:
            st.metric(
                "Power used (kW)",
                f"{site_metrics.site_power_used_kw:.1f} kW",
            )

        with u3:
            st.metric(
                "Power per ASIC (incl. overhead)",
                f"{site_metrics.power_per_asic_kw:.2f} kW",
            )

        # -----------------------------------------------------
        # ROW 3 — EFFICIENCY ECONOMICS
        # -----------------------------------------------------
        e1, e2, e3 = st.columns(3)

        with e1:
            st.metric(
                "Net revenue per kW / day",
                f"£{site_metrics.net_revenue_per_kw_gbp_per_day:,.2f}",
            )

        with e2:
            st.metric(
                "Electricity cost / day",
                f"£{site_metrics.site_power_cost_gbp_per_day:,.0f}",
            )

        with e3:
            st.metric(
                "ASICs supported",
                f"{site_metrics.asics_supported}",
            )

        # Footnote: spare capacity
        st.caption(
            f"Approx. {site_metrics.spare_capacity_kw:.1f} kW spare capacity remains "
            "for future expansion or overheads."
        )

        # Debug expander
        with st.expander("🔍 Debug: raw input & derived data", expanded=False):
            st.markdown("**Site inputs**")
            st.json(asdict(site_inputs))

            st.markdown("**Selected miner**")
            st.json(asdict(selected_miner))

            st.markdown("**Derived site metrics**")
            st.json(asdict(site_metrics))

    # ---------------------------------------------------------
    # SCENARIOS TAB
    # ---------------------------------------------------------
    with tab_scenarios:
        # Pass the derived SiteMetrics into the scenarios view so it can
        # build real project-level economics. Extra kwargs are ignored.
        render_scenarios_and_risk(
            site=site_metrics,
            miner=selected_miner,
            network_data=network_data,
            usd_to_gbp=network_data.usd_to_gbp,
        )

    # ---------------------------------------------------------
    # ASSUMPTIONS TAB
    # ---------------------------------------------------------
    with tab_assumptions:
        render_assumptions_and_methodology()
