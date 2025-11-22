# src/ui/layout.py
from __future__ import annotations

import base64
import locale
import textwrap
from datetime import datetime, timezone

import altair as alt
import pandas as pd
import streamlit as st

from src.config import settings
from src.config.settings import LIVE_DATA_CACHE_TTL_S
from src.config.version import APP_VERSION, PRIVACY_URL, TERMS_URL
from src.core.btc_forecast_engine import (
    annual_totals,
    build_monthly_forecast,
    forecast_to_dataframe,
)
from src.core.capex import compute_capex_breakdown
from src.core.fiat_forecast_engine import (
    build_fiat_monthly_forecast,
    fiat_forecast_to_dataframe,
)
from src.core.forecast_utils import build_halving_dates, build_unified_monthly_table
from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.core.miner_analytics import (
    build_viability_summary,
    compute_breakeven_points,
    compute_payback_points,
)
from src.core.scenario_calculations import build_base_annual_from_site_metrics
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import run_scenario
from src.core.site_metrics import SiteMetrics, compute_site_metrics
from src.ui.assumptions import render_assumptions_and_methodology
from src.ui.forecast_types import BTCForecastContext, FiatForecastContext
from src.ui.miner_selection import (
    get_current_selected_miner,
    load_miner_options,
    maybe_autoselect_miner,
    render_miner_picker,
)
from src.ui.pdf_export import build_pdf_report
from src.ui.scenario_1 import render_scenario_panel
from src.ui.scenarios import (
    _build_dummy_base_years,
    _derive_project_years,
    _render_scenario_comparison,
    render_scenarios_and_risk,
)
from src.ui.site_inputs import render_site_inputs

# Try to honor the user's locale for date formatting; fallback to settings.
try:
    locale.setlocale(locale.LC_TIME, "")
except Exception:
    pass


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
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=None,
            hashprice_as_of_utc=None,
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
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=None,
            hashprice_as_of_utc=None,
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
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=None,
            hashprice_as_of_utc=None,
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

    if selected_miner is None:
        return SiteMetrics(
            asics_supported=0,
            power_per_asic_kw=0.0,
            site_power_used_kw=0.0,
            site_power_available_kw=site_power_kw,
            spare_capacity_kw=site_power_kw,
            site_btc_per_day=0.0,
            site_revenue_usd_per_day=0.0,
            site_revenue_gbp_per_day=0.0,
            site_power_cost_gbp_per_day=0.0,
            site_net_revenue_gbp_per_day=0.0,
            net_revenue_per_kw_gbp_per_day=0.0,
            net_revenue_per_kwh_gbp=0.0,
        )

    return compute_site_metrics(
        miner=selected_miner,
        network=network_data,
        site_power_kw=site_power_kw,
        electricity_cost_per_kwh_gbp=electricity_cost_per_kwh_gbp,
        uptime_pct=uptime_pct,
        cooling_overhead_pct=cooling_overhead_pct,
        usd_to_gbp_rate=network_data.usd_to_gbp,
    )


# ---------------------------------------------------------
# Helper: run scenarios for snapshot view
# ---------------------------------------------------------
def _build_scenario_results_snapshot(
    site_metrics: SiteMetrics,
    usd_to_gbp: float,
    client_share_pct: float,
    go_live_date,
):
    project_years = _derive_project_years(site_metrics)

    if isinstance(site_metrics, SiteMetrics) and site_metrics.asics_supported > 0:
        base_years = build_base_annual_from_site_metrics(
            site=site_metrics,
            project_years=project_years,
            go_live_date=go_live_date,
        )
    else:
        base_years = _build_dummy_base_years(
            project_years=project_years,
            usd_to_gbp=usd_to_gbp,
        )

    if not base_years:
        return None

    scenarios_cfg = build_default_scenarios(
        client_share_override=client_share_pct / 100.0,
    )

    total_capex_gbp: float = 0.0

    base_result = run_scenario(
        name="Base case",
        base_years=base_years,
        cfg=scenarios_cfg["base"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )
    best_result = run_scenario(
        name="Best case",
        base_years=base_years,
        cfg=scenarios_cfg["best"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )
    worst_result = run_scenario(
        name="Worst case",
        base_years=base_years,
        cfg=scenarios_cfg["worst"],
        total_capex_gbp=total_capex_gbp,
        usd_to_gbp=usd_to_gbp,
    )

    st.session_state["pdf_scenarios"] = {
        "base": base_result,
        "best": best_result,
        "worst": worst_result,
        "client_share_pct": client_share_pct,
    }
    st.session_state["scenario_client_share_pct"] = client_share_pct

    return base_result, best_result, worst_result


# ---------------------------------------------------------
# Main dashboard
# ---------------------------------------------------------
def render_dashboard() -> None:
    st.title("21Scot bitcoin dashboard")
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

    data_timestamp_utc = (
        network_data.as_of_utc.strftime("%Y-%m-%d %H:%M UTC")
        if network_data.as_of_utc
        else "N/A"
    )
    hashprice_timestamp_utc = (
        network_data.hashprice_as_of_utc.strftime("%Y-%m-%d %H:%M UTC")
        if getattr(network_data, "hashprice_as_of_utc", None)
        else data_timestamp_utc
    )
    page_render_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with st.sidebar.expander("BTC network data in use", expanded=True):
        st.metric("BTC price (USD)", f"${network_data.btc_price_usd:,.0f}")
        st.metric("Difficulty", format_engineering(network_data.difficulty))
        st.metric("Block subsidy", f"{network_data.block_subsidy_btc} BTC")
        st.metric("Block height", network_data.block_height or "N/A")
        st.caption("These values drive all BTC/day and revenue calculations.")
        st.caption(f"Data timestamp (UTC): {data_timestamp_utc}")
        st.caption(f"Page render time (UTC): {page_render_utc}")

    with st.sidebar.expander("Foreign exchange value", expanded=True):
        st.metric("USD/GBP exchange rate", f"${network_data.usd_to_gbp:.3f}")
        st.caption("This value drives all the USD to GBP currency conversions.")
        st.caption(f"Data timestamp (UTC): {data_timestamp_utc}")
        st.caption(f"Page render time (UTC): {page_render_utc}")

    with st.sidebar.expander("Hashprice (Luxor)", expanded=True):
        hashprice_val = getattr(network_data, "hashprice_usd_per_ph_day", None)
        if hashprice_val is not None:
            st.metric(
                "Hashprice",
                f"${hashprice_val:,.2f} / PH/s / day",
                help=(
                    "Luxor hashprice in USD per PH/s per day. "
                    "hashrate-index API source."
                ),
            )
            st.caption(f"Data timestamp (UTC): {hashprice_timestamp_utc}")
        else:
            st.info(
                "Hashprice unavailable right now (Luxor endpoint), showing N/A. "
                "BTC/d calculations still use difficulty & subsidy."
            )
        st.caption(f"Page render time (UTC): {page_render_utc}")

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
        st.markdown("## 1. Set up your site parameters")

        # Inputs + timeline
        site_inputs = render_site_inputs()

        # Derived effective power (kW) once user starts entering data
        load_factor = (site_inputs.uptime_pct or 0) / 100.0
        effective_power_kw = site_inputs.site_power_kw * load_factor
        st.session_state["effective_power_kw"] = effective_power_kw

        # Try to auto-select a miner only after the user edits inputs
        maybe_autoselect_miner(
            site_power_kw=site_inputs.site_power_kw,
            power_price_gbp_per_kwh=site_inputs.electricity_cost,
            uptime_pct=site_inputs.uptime_pct,
            network=network_data,
        )

        # Miner selection (user-picked or auto-selected)
        selected_miner = get_current_selected_miner()

        # Compute site metrics from the current inputs
        site_metrics = build_site_metrics_from_inputs(
            site_inputs=site_inputs,
            selected_miner=selected_miner,
            network_data=network_data,
        )
        if site_metrics.asics_supported > 0:
            capex_breakdown = compute_capex_breakdown(
                site_metrics.asics_supported,
                usd_to_gbp=network_data.usd_to_gbp,
            )
        else:
            capex_breakdown = None

        st.session_state["pdf_site_inputs"] = site_inputs
        st.session_state["pdf_selected_miner"] = selected_miner
        st.session_state["pdf_site_metrics"] = site_metrics
        st.session_state["pdf_capex_breakdown"] = capex_breakdown

        if selected_miner is None:
            st.info(
                "Enter site power, £/kWh, and uptime to begin. "
                "Once inputs are provided, we will choose the fastest payback miner, "
                "and you can override it via the picker."
            )
        else:
            st.markdown("---")
            st.markdown("## 2. Your site daily performance")
            st.markdown(
                "We've calculated these values with today's network data, the most "
                "efficient hardware that's available and your cost of power, so they "
                "provide an accurate snapshot of your site's potential."
            )

            # Power utilisation (%)
            if site_metrics.site_power_available_kw > 0:
                power_used_pct = (
                    site_metrics.site_power_used_kw
                    / site_metrics.site_power_available_kw
                    * 100.0
                )
            else:
                power_used_pct = 0.0

            metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
            with metrics_col1:
                st.metric(
                    "Net income / kWh",
                    f"£{site_metrics.net_revenue_per_kwh_gbp:,.3f}",
                    help=(
                        "Net income divided by the kWh of energy actually used per "
                        "day. Shows the economic value (£/kWh) of routing your energy "
                        "into Bitcoin mining instead of alternative uses."
                    ),
                )

            with metrics_col2:
                st.metric(
                    "Net income / day",
                    f"£{site_metrics.site_net_revenue_gbp_per_day:,.0f}",
                    help=(
                        "Gross revenue minus electricity cost for all ASICs on site, "
                        "after applying your uptime assumption. This is the net "
                        "income the site generates per day before tax and other "
                        "overheads."
                    ),
                )
            with metrics_col3:
                st.metric(
                    "BTC mined / day",
                    f"{site_metrics.site_btc_per_day:.5f} BTC",
                    help=(
                        "Total BTC expected per day from all ASICs at the configured "
                        "uptime, using the current network difficulty and block "
                        "subsidy."
                    ),
                )

            with st.expander("Site performance details...", expanded=False):
                # Row 1 — Financials
                f1, f2, f3 = st.columns(3)
                with f1:
                    st.metric(
                        "Net income / day",
                        f"£{site_metrics.site_net_revenue_gbp_per_day:,.0f}",
                        help=(
                            "Gross revenue minus electricity cost for all ASICs on "
                            "site, after applying your uptime assumption. This is the "
                            "net income the site generates per day before tax and "
                            "other overheads."
                        ),
                    )
                with f2:
                    st.metric(
                        "Gross revenue / day",
                        f"£{site_metrics.site_revenue_gbp_per_day:,.0f}",
                        help=(
                            "Expected revenue for one ASIC (based on BTC price, "
                            "difficulty, and block reward), multiplied by the number "
                            "of ASICs running, adjusted for uptime, and converted from "
                            "USD to GBP using the FX rate in the sidebar."
                        ),
                    )
                with f3:
                    st.metric(
                        "Electricity cost / day",
                        f"£{site_metrics.site_power_cost_gbp_per_day:,.0f}",
                        help=(
                            "Estimated electricity spend per day for running all "
                            "ASICs, including cooling/overhead power. Based on site "
                            "kWh usage, your electricity tariff (£/kWh), and uptime."
                        ),
                    )

                # Row 2 — Utilisation & physics
                u1, u2, u3 = st.columns(3)
                with u1:
                    st.metric(
                        "Site power utilisation (%)",
                        f"{power_used_pct:.1f} %",
                        help=(
                            "How much of your available site power is currently being "
                            "used by ASICs (including cooling/overhead). Calculated as "
                            "used kW ÷ available kW."
                        ),
                    )
                with u2:
                    st.metric(
                        "Power used (kW)",
                        f"{site_metrics.site_power_used_kw:.1f} kW",
                        help=(
                            "Total electrical load drawn by all ASICs, including "
                            "cooling and overhead. This is the kW actually "
                            "committed to mining when the site is fully running."
                        ),
                    )
                with u3:
                    st.metric(
                        "Power per ASIC (incl. overhead)",
                        f"{site_metrics.power_per_asic_kw:.2f} kW",
                        help=(
                            "Effective kW per ASIC including cooling/overhead. "
                            "Calculated from the miner nameplate power plus the "
                            "cooling/overhead percentage set in the inputs."
                        ),
                    )

                # Row 3 — Efficiency & scale
                e1, e2, e3 = st.columns(3)
                with e1:
                    st.metric(
                        "Net income / kWh",
                        f"£{site_metrics.net_revenue_per_kwh_gbp:,.3f}",
                        help=(
                            "Net income divided by the kWh of energy actually used per "
                            "day. Shows the economic value (£/kWh) of routing your "
                            "energy into Bitcoin mining instead of alternative uses."
                        ),
                    )
                with e2:
                    st.metric(
                        "ASICs supported",
                        f"{site_metrics.asics_supported}",
                        help=(
                            "Maximum number of ASICs the site can support with the "
                            "available power, after accounting for cooling/overhead. "
                            "Calculated as site power capacity ÷ power per ASIC."
                        ),
                    )
                with e3:
                    st.metric(
                        "BTC mined / day",
                        f"{site_metrics.site_btc_per_day:.5f} BTC",
                        help=(
                            "Total BTC expected per day from all ASICs at the "
                            "configured uptime, using the current network difficulty "
                            "and block subsidy."
                        ),
                    )

                st.caption(
                    f"Approx. {site_metrics.spare_capacity_kw:.1f} kW spare capacity "
                    "remains for future expansion or overheads."
                )

            with st.expander("Miner details...", expanded=False):
                supplier = selected_miner.supplier or "—"
                price = (
                    f"${selected_miner.price_usd:,.0f}"
                    if selected_miner.price_usd
                    else "—"
                )
                st.markdown(
                    f"**Supplier:** {supplier} · **Model:** {selected_miner.name} · "
                    f"**Indicative price (USD):** {price}"
                )

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric(
                        label="Efficiency",
                        value=f"{selected_miner.efficiency_j_per_th:.1f} J/TH",
                    )
                with c2:
                    st.metric(
                        label="Hashrate",
                        value=f"{selected_miner.hashrate_th:.0f} TH/s",
                    )
                    with c3:
                        st.metric(
                            label="Power draw",
                            value=f"{selected_miner.power_w} W",
                        )

                selected_miner = render_miner_picker(
                    label="Alternative ASIC miners (by efficiency)",
                )

                # Breakeven & payback charts for available miners
                with st.expander("Breakeven & payback (all miners)...", expanded=False):
                    miners = list(load_miner_options())
                    breakeven_points = compute_breakeven_points(
                        miners=miners,
                        network=network_data,
                        uptime_pct=site_inputs.uptime_pct,
                    )
                    breakeven_df = pd.DataFrame(
                        [
                            {
                                "miner": pt.miner,
                                "efficiency_j_per_th": pt.efficiency_j_per_th,
                                "breakeven_price_gbp_per_kwh": (
                                    pt.breakeven_price_gbp_per_kwh
                                ),
                            }
                            for pt in breakeven_points
                            if pt.breakeven_price_gbp_per_kwh is not None
                        ]
                    )

                    if not breakeven_df.empty:
                        rule_df = pd.DataFrame(
                            {
                                "breakeven_price_gbp_per_kwh": [
                                    site_inputs.electricity_cost
                                ]
                            }
                        )
                        breakeven_chart = (
                            alt.Chart(breakeven_df)
                            .mark_point(filled=True, size=80)
                            .encode(
                                x=alt.X(
                                    "breakeven_price_gbp_per_kwh:Q",
                                    title="Breakeven power price (£/kWh)",
                                ),
                                y=alt.Y(
                                    "efficiency_j_per_th:Q",
                                    title="Efficiency (J/TH)",
                                ),
                                color=alt.Color(
                                    "miner:N", legend=alt.Legend(title="Miner")
                                ),
                                tooltip=[
                                    alt.Tooltip("miner:N", title="Miner"),
                                    alt.Tooltip(
                                        "breakeven_price_gbp_per_kwh:Q",
                                        title="Breakeven (£/kWh)",
                                        format=".4f",
                                    ),
                                    alt.Tooltip(
                                        "efficiency_j_per_th:Q",
                                        title="Efficiency (J/TH)",
                                        format=".1f",
                                    ),
                                ],
                            )
                            .properties(
                                title="Breakeven power price per miner", height=320
                            )
                        )
                        breakeven_rule = (
                            alt.Chart(rule_df)
                            .mark_rule(color="red", strokeDash=[4, 4])
                            .encode(
                                x="breakeven_price_gbp_per_kwh:Q",
                                tooltip=[
                                    alt.Tooltip(
                                        "breakeven_price_gbp_per_kwh:Q",
                                        title="Current power price (£/kWh)",
                                        format=".3f",
                                    )
                                ],
                            )
                        )
                        breakeven_chart = breakeven_chart + breakeven_rule
                        st.altair_chart(breakeven_chart, width="stretch")

                        # Tabular view
                        with st.expander("Miner breakeven table...", expanded=False):
                            # Join in capex (£) and p/kWh display
                            price_map = {
                                m.name: (m.price_usd or 0.0) * network_data.usd_to_gbp
                                for m in miners
                            }
                            table_df = breakeven_df.copy()
                            table_df["capex_gbp"] = table_df["miner"].map(price_map)
                            table_df["breakeven_price_p_per_kwh"] = (
                                table_df["breakeven_price_gbp_per_kwh"] * 100
                            )
                            table_df = table_df.sort_values(
                                by="breakeven_price_p_per_kwh", ascending=False
                            )
                            table_df = table_df.rename(
                                columns={
                                    "miner": "Miner",
                                    "efficiency_j_per_th": "Efficiency (J/TH)",
                                    "capex_gbp": "Capex (£)",
                                    "breakeven_price_p_per_kwh": (
                                        "Breakeven price (p/kWh)"
                                    ),
                                }
                            )
                            display_cols = [
                                "Miner",
                                "Breakeven price (p/kWh)",
                                "Efficiency (J/TH)",
                                "Capex (£)",
                            ]
                            table_df = table_df[display_cols].reset_index(drop=True)
                            st.dataframe(
                                table_df.style.format(
                                    {
                                        "Efficiency (J/TH)": "{:.1f}",
                                        "Capex (£)": "£{:,.0f}",
                                        "Breakeven price (p/kWh)": "{:.2f}",
                                    },
                                    na_rep="—",
                                ),
                                width="stretch",
                                hide_index=True,
                            )
                    else:
                        st.info("No breakeven data available for current inputs.")

                    power_prices = [p / 1000 for p in range(5, 151, 5)]
                    if (
                        site_inputs.electricity_cost
                        and site_inputs.electricity_cost not in power_prices
                    ):
                        power_prices.append(site_inputs.electricity_cost)
                    breakeven_map_for_payback = {
                        row["miner"]: row["breakeven_price_gbp_per_kwh"]
                        for _, row in breakeven_df.iterrows()
                    }
                    payback_cap_days = 5000
                    payback_points = compute_payback_points(
                        miners=miners,
                        network=network_data,
                        uptime_pct=site_inputs.uptime_pct,
                        power_prices_gbp=power_prices,
                        breakeven_map=breakeven_map_for_payback,
                        cap_days=payback_cap_days,
                    )
                    payback_df = pd.DataFrame(
                        [
                            {
                                "miner": pt.miner,
                                "efficiency_j_per_th": pt.efficiency_j_per_th,
                                "power_price_gbp_per_kwh": pt.power_price_gbp_per_kwh,
                                "payback_days": pt.payback_days,
                            }
                            for pt in payback_points
                            if pt.payback_days is not None
                        ]
                    )
                    if not payback_df.empty:

                        rule_df = pd.DataFrame(
                            {"power_price_gbp_per_kwh": [site_inputs.electricity_cost]}
                        )
                        payback_chart = (
                            alt.Chart(payback_df)
                            .mark_line()
                            .encode(
                                x=alt.X(
                                    "power_price_gbp_per_kwh:Q",
                                    title="Power price (£/kWh)",
                                ),
                                y=alt.Y(
                                    "payback_days:Q",
                                    title="Simple payback (days)",
                                ),
                                color=alt.Color(
                                    "miner:N", legend=alt.Legend(title="Miner")
                                ),
                                tooltip=[
                                    alt.Tooltip("miner:N", title="Miner"),
                                    alt.Tooltip(
                                        "power_price_gbp_per_kwh:Q",
                                        title="Power price (£/kWh)",
                                        format=".3f",
                                    ),
                                    alt.Tooltip(
                                        "payback_days:Q",
                                        title="Payback (days)",
                                        format=".0f",
                                    ),
                                ],
                            )
                            .properties(
                                title="Payback period vs power price", height=360
                            )
                        )
                        payback_rule = (
                            alt.Chart(rule_df)
                            .mark_rule(color="red", strokeDash=[4, 4])
                            .encode(
                                x="power_price_gbp_per_kwh:Q",
                                tooltip=[
                                    alt.Tooltip(
                                        "power_price_gbp_per_kwh:Q",
                                        title="Current power price (£/kWh)",
                                        format=".3f",
                                    )
                                ],
                            )
                        )
                        payback_chart = payback_chart + payback_rule
                        st.altair_chart(payback_chart, width="stretch")

                        # Discrete payback table
                        with st.expander("Payback (discrete) table...", expanded=False):
                            # Offer a set of power prices (in pence) for the table
                            available_prices = sorted(
                                {
                                    round(p * 100, 1)
                                    for p in payback_df[
                                        "power_price_gbp_per_kwh"
                                    ].unique()
                                }
                            )
                            default_prices = [
                                p for p in available_prices if 3.0 <= p <= 7.0
                            ] or available_prices[:5]
                            selected_pence = st.multiselect(
                                "Pick a set of power prices you charted (pence/kWh):",
                                options=available_prices,
                                default=default_prices,
                                help=(
                                    "These correspond to the power price axis on the "
                                    "payback chart."
                                ),
                            )

                            if selected_pence:
                                sel_prices_gbp = [p / 100 for p in selected_pence]
                                df_subset = payback_df[
                                    payback_df["power_price_gbp_per_kwh"].isin(
                                        sel_prices_gbp
                                    )
                                ].copy()
                                df_subset["price_label"] = (
                                    df_subset["power_price_gbp_per_kwh"] * 100
                                ).round(1).astype(str) + "p"

                                pivot = df_subset.pivot_table(
                                    index="miner",
                                    columns="price_label",
                                    values="payback_days",
                                    aggfunc="first",
                                )
                                pivot = pivot.reindex(index=[m.name for m in miners])

                                # Reorder columns based on selected_pence order
                                col_order = [(p, f"{p:.1f}p") for p in selected_pence]
                                pivot = pivot[
                                    [
                                        label
                                        for _, label in col_order
                                        if label in pivot.columns
                                    ]
                                ]

                                pivot = pivot.reset_index().rename(
                                    columns={"miner": "Miner"}
                                )

                                st.dataframe(
                                    pivot.style.format(
                                        {col: "{:.0f}" for col in pivot.columns[1:]},
                                        na_rep="—",
                                    ),
                                    width="stretch",
                                    hide_index=True,
                                )
                            else:
                                st.info(
                                    "Select one or more power prices to populate the "
                                    "table."
                                )

                        # Unified viability/payback chart + summary table
                        breakeven_map = {
                            row["miner"]: row["breakeven_price_gbp_per_kwh"]
                            for _, row in breakeven_df.iterrows()
                        }
                        site_price = site_inputs.electricity_cost

                        payback_lines_df = payback_df.copy()
                        payback_lines_df["breakeven_price_gbp_per_kwh"] = (
                            payback_lines_df["miner"].map(breakeven_map)
                        )
                        payback_lines_df["viable"] = (
                            payback_lines_df["breakeven_price_gbp_per_kwh"]
                            >= site_price
                        )

                        viability_chart = alt.layer(
                            alt.Chart(payback_lines_df)
                            .mark_line()
                            .encode(
                                x=alt.X(
                                    "power_price_gbp_per_kwh:Q",
                                    title="Power price (£/kWh)",
                                ),
                                y=alt.Y(
                                    "payback_days:Q",
                                    title="Simple payback (days)",
                                ),
                                color=alt.Color(
                                    "miner:N", legend=alt.Legend(title="Miner")
                                ),
                                opacity=alt.condition(
                                    alt.datum.viable,
                                    alt.value(1.0),
                                    alt.value(0.4),
                                ),
                                strokeDash=alt.condition(
                                    alt.datum.viable,
                                    alt.value([1, 0]),
                                    alt.value([4, 3]),
                                ),
                                tooltip=[
                                    alt.Tooltip("miner:N", title="Miner"),
                                    alt.Tooltip(
                                        "power_price_gbp_per_kwh:Q",
                                        title="Power price (£/kWh)",
                                        format=".3f",
                                    ),
                                    alt.Tooltip(
                                        "payback_days:Q",
                                        title="Payback (days)",
                                        format=".0f",
                                    ),
                                ],
                            ),
                            alt.Chart(breakeven_df)
                            .mark_point(filled=True, size=80)
                            .encode(
                                x="breakeven_price_gbp_per_kwh:Q",
                                y=alt.value(0),
                                color=alt.Color(
                                    "miner:N", legend=alt.Legend(title="Miner")
                                ),
                                tooltip=[
                                    alt.Tooltip("miner:N", title="Miner"),
                                    alt.Tooltip(
                                        "breakeven_price_gbp_per_kwh:Q",
                                        title="Breakeven (£/kWh)",
                                        format=".4f",
                                    ),
                                ],
                            ),
                            alt.Chart(rule_df)
                            .mark_rule(color="red", strokeDash=[4, 4])
                            .encode(
                                x="power_price_gbp_per_kwh:Q",
                                tooltip=[
                                    alt.Tooltip(
                                        "power_price_gbp_per_kwh:Q",
                                        title="Site price (£/kWh)",
                                        format=".3f",
                                    )
                                ],
                            ),
                        ).properties(
                            title="Unified payback and breakeven view",
                            height=380,
                        )
                        st.altair_chart(viability_chart, width="stretch")

                        # Summary table: viability + breakeven + payback at site price
                        site_payback = build_viability_summary(
                            miners=miners,
                            breakeven_map=breakeven_map,
                            site_price_gbp_per_kwh=site_price,
                            payback_points=payback_points,
                        )
                        summary_df = pd.DataFrame(site_payback)
                        if not summary_df.empty:
                            summary_df = summary_df.sort_values(
                                by=["Viable at site", "Breakeven price (p/kWh)"],
                                ascending=[False, False],
                            )
                            with st.expander(
                                "Unified payback and breakeven details...",
                                expanded=False,
                            ):
                                st.dataframe(
                                    summary_df.style.format(
                                        {
                                            "Breakeven price (p/kWh)": "{:.2f}",
                                            "Payback at site price (days)": "{:.0f}",
                                        },
                                        na_rep="—",
                                    ),
                                    width="stretch",
                                    hide_index=True,
                                )
                    else:
                        st.info("No payback data available for current inputs.")

            st.markdown("---")
            st.markdown("## 3. Your financial forecasts")

            st.markdown(
                "These forecasts show how your selected revenue share applies across "
                "the base, best, and worst scenarios using your inputs."
            )

            default_share_pct = int(
                settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE * 100
            )
            client_share_pct = (
                st.session_state.get("overview_client_share_pct")
                or st.session_state.get("scenario_client_share_pct")
                or st.session_state.get("pdf_scenarios", {}).get("client_share_pct")
                or default_share_pct
            )

            scenario_results = _build_scenario_results_snapshot(
                site_metrics=site_metrics,
                usd_to_gbp=network_data.usd_to_gbp,
                client_share_pct=client_share_pct,
                go_live_date=site_inputs.go_live_date,
            )

            if scenario_results:
                base_result, best_result, worst_result = scenario_results

                _render_scenario_comparison(
                    base_result=base_result,
                    best_result=best_result,
                    worst_result=worst_result,
                    heading="Scenario comparison table",
                )

                with st.expander("Scenario details...", expanded=False):
                    client_share_pct = st.slider(
                        "Your share of BTC revenue (%)",
                        min_value=0,
                        max_value=100,
                        value=int(client_share_pct),
                        step=1,
                        key="overview_client_share_pct",
                    )
                    st.session_state["scenario_client_share_pct"] = client_share_pct

                    updated_results = _build_scenario_results_snapshot(
                        site_metrics=site_metrics,
                        usd_to_gbp=network_data.usd_to_gbp,
                        client_share_pct=client_share_pct,
                        go_live_date=site_inputs.go_live_date,
                    )
                    if updated_results:
                        base_result, best_result, worst_result = updated_results

                    with st.expander("Base case...", expanded=True):
                        render_scenario_panel(
                            base_result,
                            capex_breakdown=capex_breakdown,
                        )
                    with st.expander("Best case...", expanded=False):
                        render_scenario_panel(
                            best_result,
                            capex_breakdown=capex_breakdown,
                        )
                    with st.expander("Worst case...", expanded=False):
                        render_scenario_panel(
                            worst_result,
                            capex_breakdown=capex_breakdown,
                        )
            else:
                st.info("Project-level scenarios are unavailable until inputs are set.")

            btc_ctx = _render_btc_monthly_forecast(
                site_metrics, site_inputs, network_data
            )
            fiat_ctx = _render_fiat_monthly_forecast(
                site_metrics, site_inputs, network_data, btc_ctx
            )
            _render_unified_forecast_table(network_data, btc_ctx, fiat_ctx)

    # ---------------------------------------------------------
    # SCENARIOS TAB
    # ---------------------------------------------------------
    with tab_scenarios:
        if selected_miner is None:
            st.info("Provide site inputs and select a miner to view scenarios.")
        else:
            # Pass the derived SiteMetrics into the scenarios view so it can
            # build real project-level economics. Extra kwargs are ignored.
            render_scenarios_and_risk(
                site=site_metrics,
                miner=selected_miner,
                network_data=network_data,
                usd_to_gbp=network_data.usd_to_gbp,
                go_live_date=site_inputs.go_live_date,
            )

    # ---------------------------------------------------------
    # ASSUMPTIONS TAB
    # ---------------------------------------------------------
    with tab_assumptions:
        render_assumptions_and_methodology()

    st.markdown("---")

    render_pdf_download_section()
    render_footer()


def _render_btc_monthly_forecast(
    site_metrics: SiteMetrics, site_inputs, network_data: NetworkData
) -> BTCForecastContext:
    ctx = BTCForecastContext(
        monthly_rows=[],
        monthly_df=pd.DataFrame(),
        fee_growth_pct=float(getattr(settings, "DEFAULT_FEE_GROWTH_PCT", 0)),
        difficulty_growth_pct=float(
            getattr(settings, "DEFAULT_HASHRATE_GROWTH_PCT", 0)
        ),
    )
    with st.expander("BTC forecast (monthly)...", expanded=False):
        st.markdown("**BTC forecast (monthly)**")

        difficulty_growth_pct = st.slider(
            "Hashrate growth (%/year)",
            min_value=0,
            max_value=100,
            value=int(settings.DEFAULT_HASHRATE_GROWTH_PCT),
            step=1,
            help="Annual growth rate for global network hashrate.",
        )
        fee_growth_pct = st.slider(
            "Fee growth (%/year)",
            min_value=0,
            max_value=100,
            value=int(getattr(settings, "DEFAULT_FEE_GROWTH_PCT", 0)),
            step=1,
            help="Annual growth rate for transaction fees per block.",
        )
        ctx.fee_growth_pct = float(fee_growth_pct)
        ctx.difficulty_growth_pct = float(difficulty_growth_pct)

        monthly_rows = build_monthly_forecast(
            site=site_metrics,
            start_date=site_inputs.go_live_date,
            project_years=_derive_project_years(site_metrics),
            fee_growth_pct_per_year=float(fee_growth_pct),
            hashrate_growth_pct_per_year=float(difficulty_growth_pct),
        )
        ctx.monthly_rows = monthly_rows
        monthly_df = forecast_to_dataframe(monthly_rows)
        ctx.monthly_df = monthly_df

        if monthly_df.empty:
            st.info("Monthly forecast unavailable for current inputs.")
            return ctx

        monthly_df["Month"] = pd.to_datetime(monthly_df["Month"])
        bar_color = "#cfd2d6"
        y_pad_pct = getattr(settings, "HISTOGRAM_Y_PAD_PCT", 0.3) or 0.0
        y_max = monthly_df["BTC mined"].max()
        y_domain = (0, float(y_max * (1 + y_pad_pct))) if y_max > 0 else (0, 1)

        bar_layer = (
            alt.Chart(monthly_df)
            .mark_bar(color=bar_color)
            .encode(
                x=alt.X(
                    "Month:T",
                    title="Month",
                    axis=alt.Axis(format="%b '%y", labelAngle=-45),
                ),
                y=alt.Y(
                    "BTC mined:Q",
                    title="BTC mined (per month)",
                    scale=alt.Scale(domain=y_domain, nice=False),
                ),
                tooltip=[
                    alt.Tooltip("Month:T", title="Month"),
                    alt.Tooltip("BTC mined:Q", title="BTC mined", format=".5f"),
                    alt.Tooltip("Subsidy (BTC/block):Q", title="Subsidy", format=".4f"),
                    alt.Tooltip("Fee (BTC/block):Q", title="Fee", format=".6f"),
                    alt.Tooltip(
                        "Total reward (BTC/block):Q", title="Reward", format=".6f"
                    ),
                ],
            )
        )
        right_axis = (
            alt.Chart(monthly_df)
            .mark_line(opacity=0)
            .encode(
                x="Month:T",
                y=alt.Y(
                    "BTC mined:Q",
                    axis=alt.Axis(title="BTC mined (per month)", orient="right"),
                    scale=alt.Scale(domain=y_domain, nice=False),
                ),
            )
        )

        halving_layer = None
        halving_dates = build_halving_dates(
            getattr(settings, "NEXT_HALVING_DATE", None),
            int(getattr(settings, "HALVING_INTERVAL_YEARS", 4)),
            monthly_df["Month"].max().date(),
        )
        if halving_dates:
            halving_df = pd.DataFrame({"halving": halving_dates})
            halving_layer = (
                alt.Chart(halving_df)
                .mark_rule(
                    color=getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A"),
                    strokeDash=[4, 4],
                )
                .encode(x="halving:T")
            )

        layers = [bar_layer, right_axis]
        if halving_layer is not None:
            layers.append(halving_layer)
        chart = (
            alt.layer(*layers)
            .resolve_scale(y="independent")
            .properties(title="BTC forecast (monthly)", height=320)
        )
        st.altair_chart(chart, width="stretch")

        with st.expander("BTC forecast (monthly) diagnostics...", expanded=False):
            annual_df = annual_totals(monthly_rows)
            total_btc = monthly_df["BTC mined"].sum()
            st.metric("Cumulative BTC (project)", f"{total_btc:,.5f} BTC")
            if not annual_df.empty:
                st.dataframe(
                    annual_df.style.format({"BTC mined": "{:.5f}"}),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No annual totals available.")

        st.markdown(
            textwrap.dedent(
                """
We model two protocol-level effects that are outside your control:
• Block reward (subsidy halvings + transaction fees)
• Global network hashrate growth, which we map into difficulty adjustments
  to keep block time ≈ 10 minutes.

We do not explicitly model short-term block time variance or orphan blocks,
as these average out over multi-month horizons and have negligible impact
on long-term site economics.

**Clear disclaimer:** There is no accepted industry standard for forecasting
future hashrate or fee growth. We provide transparent, adjustable assumptions
so you can align the model with your own view.
                """
            ).strip()
        )

        st.dataframe(
            monthly_df.style.format(
                {
                    "Month": _format_month,
                    "BTC mined": "{:.5f}",
                    "Total reward (BTC/block)": "{:.6f}",
                    "Subsidy (BTC/block)": "{:.4f}",
                    "Fee (BTC/block)": "{:.6f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    return ctx


def _render_fiat_monthly_forecast(
    site_metrics: SiteMetrics,
    site_inputs,
    network_data: NetworkData,
    btc_ctx: BTCForecastContext,
) -> FiatForecastContext:
    ctx = FiatForecastContext(
        fiat_rows=[],
        fiat_df=pd.DataFrame(),
        price_growth_pct=float(getattr(settings, "DEFAULT_BTC_PRICE_GROWTH_PCT", 0)),
    )
    with st.expander("Fiat forecast (monthly)...", expanded=False):
        price_growth_pct = st.slider(
            "BTC price growth (%/year)",
            min_value=-100,
            max_value=200,
            value=int(getattr(settings, "DEFAULT_BTC_PRICE_GROWTH_PCT", 0)),
            step=1,
            help="Annual BTC price growth, applied monthly.",
        )
        ctx.price_growth_pct = float(price_growth_pct)

        monthly_rows = btc_ctx.monthly_rows
        if not monthly_rows:
            monthly_rows = build_monthly_forecast(
                site=site_metrics,
                start_date=site_inputs.go_live_date,
                project_years=_derive_project_years(site_metrics),
                fee_growth_pct_per_year=float(
                    btc_ctx.get("fee_growth_pct", settings.DEFAULT_FEE_GROWTH_PCT)
                ),
                hashrate_growth_pct_per_year=float(
                    btc_ctx.get(
                        "difficulty_growth_pct", settings.DEFAULT_HASHRATE_GROWTH_PCT
                    )
                ),
            )
        monthly_df = btc_ctx.monthly_df
        if monthly_df is None or monthly_df.empty:
            monthly_df = forecast_to_dataframe(monthly_rows)

        fiat_rows = build_fiat_monthly_forecast(
            monthly_btc_rows=monthly_rows,
            start_price_usd=network_data.btc_price_usd,
            annual_price_growth_pct=float(price_growth_pct),
            usd_to_gbp=network_data.usd_to_gbp,
        )
        ctx.fiat_rows = fiat_rows
        fiat_df = fiat_forecast_to_dataframe(fiat_rows)
        ctx.fiat_df = fiat_df

        if fiat_df.empty:
            st.info("Fiat forecast unavailable for current inputs.")
            return ctx

        fiat_df["Month"] = pd.to_datetime(fiat_df["Month"])

        line_pad = getattr(settings, "LINE_Y_PAD_PCT", 0.3) or 0.0
        y_max = fiat_df["Revenue (GBP)"].max()
        y_domain = (0, float(y_max * (1 + line_pad))) if y_max > 0 else (0, 1)

        left_line = (
            alt.Chart(fiat_df)
            .mark_line(color=getattr(settings, "FIAT_NEUTRAL_BLUE_HEX", "#1f77b4"))
            .encode(
                x=alt.X(
                    "Month:T",
                    title="Month",
                    axis=alt.Axis(format="%b '%y", labelAngle=-45),
                ),
                y=alt.Y(
                    "Revenue (GBP):Q",
                    title="Revenue (GBP)",
                    scale=alt.Scale(domain=y_domain, nice=False),
                ),
                tooltip=[
                    alt.Tooltip("Month:T", title="Month"),
                    alt.Tooltip(
                        "Revenue (GBP):Q", title="Revenue (GBP)", format=",.0f"
                    ),
                    alt.Tooltip(
                        "BTC price (USD):Q", title="BTC price (USD)", format=",.0f"
                    ),
                    alt.Tooltip("BTC mined:Q", title="BTC mined", format=".5f"),
                ],
            )
        )
        right_axis = (
            alt.Chart(fiat_df)
            .mark_line(opacity=0)
            .encode(
                x=alt.X(
                    "Month:T",
                    title="Month",
                    axis=alt.Axis(format="%b '%y", labelAngle=-45),
                ),
                y=alt.Y(
                    "Revenue (GBP):Q",
                    axis=alt.Axis(title="Revenue (GBP)", orient="right"),
                    scale=alt.Scale(domain=y_domain, nice=False),
                ),
            )
        )

        halving_layer = None
        halving_dates = build_halving_dates(
            getattr(settings, "NEXT_HALVING_DATE", None),
            int(getattr(settings, "HALVING_INTERVAL_YEARS", 4)),
            fiat_df["Month"].max().date(),
        )
        if halving_dates:
            halving_df = pd.DataFrame({"halving": halving_dates})
            halving_layer = (
                alt.Chart(halving_df)
                .mark_rule(
                    color=getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A"),
                    strokeDash=[4, 4],
                )
                .encode(x="halving:T")
            )

        layers = [left_line, right_axis]
        if halving_layer is not None:
            layers.append(halving_layer)

        chart = (
            alt.layer(*layers)
            .resolve_scale(y="independent")
            .properties(title="Fiat forecast (monthly)", height=300)
        )
        st.altair_chart(chart, width="stretch")
        st.caption("Vertical dashed lines mark estimated halving dates.")

        st.dataframe(
            fiat_df.style.format(
                {
                    "Month": _format_month,
                    "Revenue (GBP)": "£{:,.0f}",
                    "BTC price (USD)": "${:,.0f}",
                    "BTC mined": "{:.5f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )
    return ctx


def _render_unified_forecast_table(
    network_data: NetworkData,
    btc_ctx: BTCForecastContext,
    fiat_ctx: FiatForecastContext,
):
    monthly_df = btc_ctx.monthly_df if btc_ctx else None
    fiat_df = fiat_ctx.fiat_df if fiat_ctx else None
    if monthly_df is None or fiat_df is None or monthly_df.empty or fiat_df.empty:
        return

    with st.expander("Unified BTC & Fiat forecast (monthly)...", expanded=False):
        unified_df = build_unified_monthly_table(
            monthly_df, fiat_df, usd_to_gbp=network_data.usd_to_gbp
        )

        st.dataframe(
            unified_df.style.format(
                {
                    "Month": _format_month,
                    "BTC mined": "{:.5f}",
                    "Revenue (GBP)": "£{:,.0f}",
                    "BTC price (GBP)": "£{:,.0f}",
                }
            ),
            width="stretch",
            hide_index=True,
        )


def _format_month(value):
    if pd.isna(value):
        return ""
    fmt = getattr(settings, "DATE_DISPLAY_FMT", "%d/%m/%Y")
    try:
        return value.strftime(fmt)
    except Exception:
        return str(value)


def render_footer() -> None:
    st.markdown("---")
    footer_html = (
        f"<p style='text-align: center;'>"
        f"Version {APP_VERSION} · "
        f"<a href='{TERMS_URL}' target='_blank'>Terms & Conditions</a> · "
        f"<a href='{PRIVACY_URL}' target='_blank'>Privacy Policy</a>"
        f"</p>"
    )
    st.markdown(footer_html, unsafe_allow_html=True)


def render_pdf_download_section() -> None:
    pdf_site_inputs = st.session_state.get("pdf_site_inputs")
    pdf_miner = st.session_state.get("pdf_selected_miner")
    pdf_metrics = st.session_state.get("pdf_site_metrics")
    pdf_capex = st.session_state.get("pdf_capex_breakdown")
    scenario_state = st.session_state.get("pdf_scenarios")

    if not all([pdf_site_inputs, pdf_miner, pdf_metrics, scenario_state]):
        st.info(
            "Provide site parameters and compute scenarios to enable the PDF export."
        )
        return

    scenarios = {
        key: scenario_state.get(key)
        for key in ("base", "best", "worst")
        if scenario_state.get(key)
    }
    client_share_pct = scenario_state.get("client_share_pct", 0.0)

    pdf_bytes = build_pdf_report(
        site_inputs=pdf_site_inputs,
        miner=pdf_miner,
        metrics=pdf_metrics,
        scenarios=scenarios,
        client_share_pct=client_share_pct,
        capex_breakdown=pdf_capex,
    )

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    button_html = f"""
        <style>
        .pdf-actions {{
            width: 100%;
            display: flex;
            justify-content: flex-end;
        }}
        .pdf-actions button {{
            background-color: #f2f2f2;
            color: #1f1f1f;
            border: 1px solid #d0d0d0;
            border-radius: 0.25rem;
            padding: 0.35rem 0.9rem;
            font-weight: 600;
            cursor: pointer;
            width: 140px;
        }}
        .pdf-actions button:hover {{
            background-color: #e5e5e5;
        }}
        </style>
        <script>
            const pdfData = "{pdf_base64}";
            function buildBlobUrl() {{
                const byteCharacters = atob(pdfData);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {{
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], {{type: 'application/pdf'}});
                return URL.createObjectURL(blob);
            }}
            function openPdf() {{
                const blobUrl = buildBlobUrl();
                window.open(blobUrl, '_blank');
            }}
        </script>
        <div style="
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:1rem;
        ">
            <h3 style="margin:0;">Your proposal for a 21Scot data centre</h3>
            <button onclick="openPdf()">View pdf</button>
        </div>
    """
    st.markdown(button_html, unsafe_allow_html=True)
