# src/ui/layout.py
from __future__ import annotations

# ruff: noqa: E501
import base64
import locale
import textwrap
from datetime import datetime, timezone

import altair as alt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

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
)
from src.core.forecast_utils import (
    build_halving_dates,
    build_unified_monthly_table,
    prepare_btc_display,
    prepare_fiat_display,
)
from src.core.investment_metrics import compute_investment_metrics
from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.core.miner_analytics import (
    build_viability_summary,
    compute_breakeven_points,
    compute_payback_points,
)
from src.core.miner_economics import (
    compute_miner_economics,
    compute_miner_economics_table,
    select_recommended_miner,
)
from src.core.scenario_calculations import build_base_annual_from_site_metrics
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import run_scenario
from src.core.site_metrics import SiteMetrics, compute_site_metrics
from src.ui.assumptions import render_assumptions_and_methodology
from src.ui.charts import (
    render_btc_forecast_chart,
    render_cumulative_cashflow_chart,
    render_fiat_forecast_chart,
    render_investment_summary,
    render_unified_forecast_chart,
)
from src.ui.forecast_types import BTCForecastContext, FiatForecastContext
from src.ui.learn_bitcoin import render_learn_about_bitcoin
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


def _get_forecast_growth_inputs():
    """Fetch difficulty and fee growth assumptions from session state or defaults."""
    placeholder_hashrate_key = "placeholder_hashrate_growth_pct"
    placeholder_fee_key = "placeholder_fee_growth_pct"
    difficulty_default = int(getattr(settings, "DEFAULT_HASHRATE_GROWTH_PCT", 0))
    fee_default = int(getattr(settings, "DEFAULT_FEE_GROWTH_PCT", 0))

    difficulty_growth_pct = int(
        st.session_state.get(placeholder_hashrate_key, difficulty_default)
    )
    fee_growth_pct = int(st.session_state.get(placeholder_fee_key, fee_default))
    return (
        placeholder_hashrate_key,
        placeholder_fee_key,
        difficulty_growth_pct,
        fee_growth_pct,
    )


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
# Plotly helper: miner unit economics scatter
# ---------------------------------------------------------
def _build_unit_economics_chart(df: pd.DataFrame):
    fig = px.scatter(
        df,
        x="efficiency_j_per_th",
        y="margin_gbp_per_unit_per_day",
        color="is_viable",
        hover_name="miner_name",
        custom_data=[
            "miner_name",
            "hashrate_ths",
            "power_kw",
            "capex_gbp",
        ],
        labels={
            "efficiency_j_per_th": "Efficiency (J/TH)",
            "margin_gbp_per_unit_per_day": "Daily gross margin per unit (£/day)",
            "is_viable": "Profitable at this power price?",
        },
        title="Miner unit economics vs efficiency",
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Efficiency: %{x:.1f} J/TH<br>"
            "Margin: £%{y:,.0f}/day<br>"
            "Hashrate: %{customdata[1]:.0f} TH/s<br>"
            "Power: %{customdata[2]:.2f} kW<br>"
            "CapEx: £%{customdata[3]:,.0f}"
            "<extra></extra>"
        )
    )
    fig.add_hline(
        y=0,
        line_dash="dash",
        annotation_text="Breakeven",
        annotation_position="bottom left",
    )
    fig.update_layout(
        legend_title_text="Viability",
        xaxis_title="Efficiency (J/TH) – lower is better",
        yaxis_title="Gross margin per unit (£/day)",
        title={
            "text": (
                "Miner unit economics vs efficiency"
                "<br><sup style='color:#6b7280;'>Shows how much profit each miner makes per day at your current power price.</sup>"
            )
        },
    )
    return fig


def _build_site_economics_chart(df: pd.DataFrame, include_non_viable: bool):
    # NOTE: efficiency_j_per_th -> lower is better; reverse colour scale so darker = more efficient.
    viable = df[df["is_viable"]].copy()
    viable_customdata = np.stack(
        [
            viable["site_capex_gbp"],
            viable["max_units_by_power"],
        ],
        axis=-1,
    )
    fig = px.scatter(
        viable,
        x="site_daily_margin_gbp",
        y="payback_days",
        size="max_units_by_power",
        color="efficiency_j_per_th",
        color_continuous_scale="Blues_r",
        hover_name="miner_name",
        hover_data={
            "max_units_by_power": True,
            "site_capex_gbp": True,
            "site_daily_margin_gbp": True,
            "payback_days": True,
            "efficiency_j_per_th": True,
        },
        labels={
            "site_daily_margin_gbp": "Site gross margin (£/day) – higher is better",
            "payback_days": "Payback period (days)",
            "efficiency_j_per_th": "Efficiency (J/TH) — lower is better",
        },
        title=(
            "Site-level economics by miner type"
            "<br><sup style='color:#6b7280;'>Compares site-wide profit and payback for each miner at your chosen power price. "
            "(Bottom-right = higher margins and faster payback.)</sup>"
        ),
    )

    fig.update_layout(
        xaxis_title="Site gross margin (£/day) – higher is better",
        yaxis_title="Payback (days) – lower is better",
    )
    fig.update_coloraxes(colorbar_title="Efficiency (J/TH)<br>lower is better")

    fig.update_traces(
        customdata=viable_customdata,
        hovertemplate=(
            "<b>%{hovertext}</b><br>"
            "Margin: £%{x:,.0f}/day<br>"
            "Payback: %{y:,.0f} days<br>"
            "Units supported: %{customdata[1]:,}<br>"
            "Site CapEx: £%{customdata[0]:,.0f}"
            "<extra></extra>"
        ),
    )

    if include_non_viable:
        non_viable = df[~df["is_viable"]]
        if not non_viable.empty:
            nv_customdata = np.column_stack(
                [
                    non_viable["miner_name"],
                    non_viable["site_capex_gbp"],
                ]
            )
            fig.add_trace(
                go.Scatter(
                    x=non_viable["site_daily_margin_gbp"],
                    y=non_viable["payback_days"],
                    mode="markers",
                    marker=dict(
                        size=non_viable["max_units_by_power"],
                        color="lightgray",
                        opacity=0.6,
                    ),
                    hovertext=non_viable["miner_name"],
                    hoverinfo="text",
                    customdata=nv_customdata,
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Margin: £%{x:,.0f}/day<br>"
                        "Payback: %{y:,.0f} days<br>"
                        "CapEx: £%{customdata[1]:,.0f}"
                        "<extra></extra>"
                    ),
                    name="Non-viable",
                    showlegend=True,
                )
            )

    return fig


def _build_consolidated_recommendation_chart(
    df: pd.DataFrame, include_non_viable: bool, project_years: int
):
    fig = _build_site_economics_chart(df, include_non_viable=include_non_viable)
    rec = select_recommended_miner(df, project_years)
    if rec is not None:
        fig.add_trace(
            go.Scatter(
                x=[rec["site_daily_margin_gbp"]],
                y=[rec["payback_days"]],
                mode="markers+text",
                marker=dict(
                    size=22,
                    symbol="star",
                    line=dict(width=2, color="black"),
                    color="#ffb347",
                ),
                text=[f"Recommended: {rec['miner_name']}"],
                textposition="top center",
                name="Recommended miner",
            )
        )
    return fig, rec


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
    static_hashprice = settings.DEFAULT_HASHPRICE_USD_PER_PH_DAY
    static_block_reward_btc = static_subsidy + settings.DEFAULT_FEE_BTC_PER_BLOCK
    static_hashrate_ph = (
        (144 * static_block_reward_btc * static_price) / static_hashprice
        if static_hashprice
        else None
    )

    # Explicitly static
    if not use_live:
        static_data = NetworkData(
            btc_price_usd=float(static_price),
            difficulty=float(static_diff),
            block_subsidy_btc=float(static_subsidy),
            usd_to_gbp=float(static_usd_to_gbp),
            block_height=None,
            network_hashrate_ph=static_hashrate_ph,
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=float(static_hashprice),
            hashprice_as_of_utc=datetime.now(timezone.utc),
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
            f"- USD/GBP FX: `{static_usd_to_gbp:.3f}`\n"
            f"- Hashprice: `${static_hashprice:,.2f} / PH/s / day`\n\n"
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
            network_hashrate_ph=static_hashrate_ph,
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=float(static_hashprice),
            hashprice_as_of_utc=datetime.now(timezone.utc),
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
            network_hashrate_ph=static_hashrate_ph,
            as_of_utc=datetime.now(timezone.utc),
            hashprice_usd_per_ph_day=float(static_hashprice),
            hashprice_as_of_utc=datetime.now(timezone.utc),
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
    total_capex_gbp: float | None = None,
    monthly_rows: list | None = None,
):
    project_years = _derive_project_years(site_metrics)
    if total_capex_gbp is None:
        total_capex_gbp = 0.0
    if not total_capex_gbp and st.session_state.get("pdf_capex_breakdown") is not None:
        cached_capex = getattr(
            st.session_state.get("pdf_capex_breakdown"), "total_gbp", None
        )
        if cached_capex:
            total_capex_gbp = float(cached_capex)

    if isinstance(site_metrics, SiteMetrics) and site_metrics.asics_supported > 0:
        base_years = build_base_annual_from_site_metrics(
            site=site_metrics,
            project_years=project_years,
            go_live_date=go_live_date,
            monthly_rows=monthly_rows,
            usd_to_gbp=usd_to_gbp,
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
    st.title("AD BTC mining dashboard from 21.Scot")
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
        st.sidebar.info(
            "Using static BTC price, hashprice, and USD/GBP exchange rate (live unavailable)."
        )
    else:
        st.sidebar.info(
            "Using static BTC price, hashprice, and USD/GBP exchange rate (live disabled)."
        )

    data_timestamp_utc = (
        network_data.as_of_utc.strftime("%Y-%m-%d %H:%M UTC")
        if network_data.as_of_utc
        else "N/A"
    )
    page_render_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    with st.sidebar.expander("BTC network data in use", expanded=True):
        st.metric(
            "BTC price (USD)",
            f"${network_data.btc_price_usd:,.0f}",
            help=(
                "The current market price of one bitcoin in US dollars. This value "
                "updates live and drives all mining revenue calculations."
            ),
        )
        if network_data.network_hashrate_ph is not None:
            st.metric(
                "Hashrate",
                f"{network_data.network_hashrate_ph:,.0f} PH/s",
                help=(
                    "Total computational power securing the Bitcoin network (PH/s). "
                    "Higher hashrate means more competition, slightly reducing BTC "
                    "earned per PH/s. This is an estimate based on recent block times."
                ),
            )
        hashprice_val = getattr(network_data, "hashprice_usd_per_ph_day", None)
        if hashprice_val is not None:
            st.metric(
                "Hashprice (realised)",
                f"${hashprice_val:,.2f} / PH/s / day",
                help=(
                    "Estimated USD revenue earned per PH/s of hashrate per day, "
                    "based on current BTC price, network difficulty, block rewards, "
                    "and average transaction fees."
                ),
            )
        st.caption("These values drive all BTC/day and revenue calculations.")
        st.caption(f"Data timestamp (UTC): {data_timestamp_utc}")
        st.caption(f"Page render time (UTC): {page_render_utc}")

    with st.sidebar.expander("Foreign exchange rate", expanded=True):
        st.metric(
            "Live FX rate (USD→GBP)",
            f"${network_data.usd_to_gbp:.3f}",
            help=(
                "The current exchange rate from US dollars to British pounds. "
                "Used to convert all mining revenue (USD) into GBP for forecasts. "
                "A stronger USD increases GBP revenue; a weaker USD reduces it."
            ),
        )
        st.caption(f"Data timestamp (UTC): {data_timestamp_utc}")
        st.caption(f"Page render time (UTC): {page_render_utc}")

    # ---------------------------------------------------------
    # TABS
    # ---------------------------------------------------------
    tab_overview, tab_scenarios, tab_learn, tab_assumptions, tab_faq = st.tabs(
        [
            "📊 Overview",
            "🎯 Scenarios & Risk",
            "📚 Learn about Bitcoin",
            "📋 Assumptions & Methodology",
            "❓ FAQ: Choosing your ASIC",
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
                miner_price_usd=getattr(selected_miner, "price_usd", None),
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

                # Precompute shared miner/site economics for downstream expanders
                uptime_factor = max(0.0, min(site_inputs.uptime_pct or 0, 100)) / 100.0
                overhead_factor = (
                    1.0 + max(0.0, site_inputs.cooling_overhead_pct or 0) / 100.0
                )
                miner_kwh_per_day = (
                    (selected_miner.power_w / 1000.0)
                    * 24.0
                    * uptime_factor
                    * overhead_factor
                )
                econ_single = compute_miner_economics(
                    hashrate_th=selected_miner.hashrate_th,
                    network=network_data,
                )
                btc_per_day = econ_single.btc_per_day * uptime_factor
                usd_to_gbp = network_data.usd_to_gbp or 1.0
                revenue_gbp_per_day = (
                    econ_single.revenue_usd_per_day * usd_to_gbp * uptime_factor
                )
                power_cost_gbp_per_day = miner_kwh_per_day * (
                    site_inputs.electricity_cost or 0.0
                )
                net_gbp_per_day = revenue_gbp_per_day - power_cost_gbp_per_day
                revenue_usd_per_day = econ_single.revenue_usd_per_day * uptime_factor
                power_cost_usd_per_day = (
                    power_cost_gbp_per_day / usd_to_gbp if usd_to_gbp else None
                )
                net_usd_per_day = net_gbp_per_day / usd_to_gbp if usd_to_gbp else None
                breakeven_price_gbp_per_kwh = (
                    revenue_gbp_per_day / miner_kwh_per_day
                    if miner_kwh_per_day > 0
                    else None
                )
                capex_gbp = (selected_miner.price_usd or 0.0) * network_data.usd_to_gbp
                payback_days = (
                    capex_gbp / net_gbp_per_day
                    if capex_gbp > 0 and net_gbp_per_day > 0
                    else None
                )

                miners_all = list(load_miner_options())
                breakeven_points = compute_breakeven_points(
                    miners=miners_all,
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
                    site_power_price = site_inputs.electricity_cost or 0.0
                    breakeven_df["is_viable"] = (
                        breakeven_df["breakeven_price_gbp_per_kwh"] >= site_power_price
                    )

                miner_rows = [
                    {
                        "miner_name": m.name,
                        "hashrate_ths": m.hashrate_th,
                        "power_kw": (m.power_w / 1000.0) * overhead_factor,
                        "efficiency_j_per_th": m.efficiency_j_per_th,
                        "capex_gbp": (m.price_usd or 0.0) * network_data.usd_to_gbp,
                    }
                    for m in miners_all
                ]
                miners_df = pd.DataFrame(miner_rows)
                per_th_econ = compute_miner_economics(
                    hashrate_th=1.0,
                    network=network_data,
                )
                btc_revenue_gbp_per_ths_per_day = (
                    per_th_econ.revenue_usd_per_day * network_data.usd_to_gbp
                )
                econ_df = compute_miner_economics_table(
                    miners_df=miners_df,
                    site_power_kw=site_inputs.site_power_kw,
                    elec_price_gbp_per_kwh=site_inputs.electricity_cost,
                    uptime_factor=uptime_factor,
                    btc_revenue_gbp_per_ths_per_day=btc_revenue_gbp_per_ths_per_day,
                )

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
                    miners=miners_all,
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
                # unit econ chart handled in Miner breakeven analysis expander

                with st.expander("Miner detailed analysis...", expanded=False):
                    if not econ_df.empty:
                        rec_row = select_recommended_miner(
                            econ_df, project_years=site_inputs.project_years
                        )
                        if rec_row is not None:
                            st.success(
                                f'Recommended miner[?](# "Ranks miners with positive margin by: '
                                f"1) fastest payback within the project horizon, "
                                f"2) highest site daily margin, "
                                f'3) best efficiency (lowest J/TH).") '
                                f"**{rec_row['miner_name']}** — "
                                f"{int(rec_row['max_units_by_power'])} units, "
                                f"≈ £{rec_row['site_daily_margin_gbp']:,.0f}/day, "
                                f"payback ≈ {rec_row['payback_days']:.0f} days."
                            )
                        else:
                            st.warning(
                                "No economically viable miner found for this site configuration."
                            )

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

                    # Let users experiment with alternative miners from the active catalogue.
                    picker_col1, picker_col2 = st.columns([2, 1])
                    with picker_col1:
                        picker_miner = render_miner_picker(
                            label="Try another ASIC miner",
                        )
                        if picker_miner:
                            selected_miner = picker_miner

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

                    with st.expander("ASICs advanced insights...", expanded=False):
                        top1, top2, top3 = st.columns(3)
                        with top1:
                            st.metric(
                                "Net income per ASIC / day",
                                f"£{net_gbp_per_day:,.2f}",
                                help="Gross revenue minus electricity cost for one miner.",
                            )
                        with top2:
                            st.metric(
                                "Gross revenue / ASIC / day",
                                f"£{revenue_gbp_per_day:,.2f}",
                                help=(
                                    "Revenue for one miner per day at your uptime, using "
                                    "the current BTC price, difficulty and block subsidy."
                                ),
                            )
                        with top3:
                            st.metric(
                                "Power cost / ASIC / day",
                                f"£{power_cost_gbp_per_day:,.2f}",
                                help=(
                                    "Electricity cost for one miner per day including any "
                                    "cooling/overhead load and your £/kWh input."
                                ),
                            )

                        bottom1, bottom2, bottom3 = st.columns(3)
                        with bottom1:
                            breakeven_display = (
                                f"{breakeven_price_gbp_per_kwh * 100:.2f} p/kWh"
                                if breakeven_price_gbp_per_kwh
                                else "—"
                            )
                            st.metric(
                                "Breakeven power price",
                                breakeven_display,
                                help=(
                                    "Power price where the miner's gross revenue equals its "
                                    "electricity cost."
                                ),
                            )
                        with bottom2:
                            st.metric(
                                "Energy use / ASIC / day",
                                f"{miner_kwh_per_day:,.1f} kWh",
                                help=(
                                    "Daily kWh draw for one miner at your uptime, including "
                                    "cooling/overhead load."
                                ),
                            )
                        with bottom3:
                            payback_display = (
                                f"{payback_days:,.0f} days" if payback_days else "—"
                            )
                            st.metric(
                                "Simple payback (capex)",
                                payback_display,
                                help=(
                                    "Indicative capex ÷ net daily cashflow for one miner. "
                                    "Hidden if non-viable or no price available."
                                ),
                            )

                        third1, third2, third3 = st.columns(3)
                        with third1:
                            profit_usd_display = (
                                f"${net_usd_per_day:,.2f}"
                                if net_usd_per_day is not None
                                else "—"
                            )
                            st.metric(
                                "Net income per ASIC / day (USD)",
                                profit_usd_display,
                                help="Gross revenue minus electricity cost for one miner, shown in USD.",
                            )
                        with third2:
                            revenue_usd_display = (
                                f"${revenue_usd_per_day:,.2f}"
                                if revenue_usd_per_day is not None
                                else "—"
                            )
                            st.metric(
                                "Gross revenue / ASIC / day (USD)",
                                revenue_usd_display,
                                help="Revenue per miner per day in USD at your uptime and current network snapshot.",
                            )
                        with third3:
                            power_usd_display = (
                                f"${power_cost_usd_per_day:,.2f}"
                                if power_cost_usd_per_day is not None
                                else "—"
                            )
                            st.metric(
                                "Power cost / ASIC / day (USD)",
                                power_usd_display,
                                help="Electricity cost per miner per day in USD, using your £/kWh input and FX.",
                            )

                        fourth1, _, _ = st.columns(3)
                        with fourth1:
                            st.metric(
                                "BTC mined per ASIC / day",
                                f"{btc_per_day:.6f} BTC",
                                help="Estimated BTC produced by one miner per day at your uptime.",
                            )

                        st.caption(
                            "Uses your uptime, £/kWh input and cooling/overhead load with "
                            "the current BTC network snapshot."
                        )

                    with st.container():
                        # Miner breakeven analysis (nested)
                        with st.expander("Miner breakeven analysis...", expanded=False):
                            st.markdown(
                                textwrap.dedent(
                                    """
                                    - Chart 1 gives the “miner physics & unit economics” view (efficiency vs profit at the given power price). That’s effectively the “who survives this power price?” filter.
                                    """
                                )
                            )
                            if not breakeven_df.empty:
                                chart_title = alt.TitleParams(
                                    "Breakeven power price per miner",
                                    subtitle="Which miners can operate profitably at this power price point.",
                                    subtitleColor="#6b7280",
                                    subtitleFontSize=11,
                                )
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
                                            "is_viable:N",
                                            title="Viability at your power price",
                                            scale=alt.Scale(
                                                domain=[True, False],
                                                range=["#2563eb", "#d1d5db"],
                                            ),
                                            legend=alt.Legend(
                                                orient="right",
                                                labelExpr="datum.value ? 'Appropriate' : 'Not suitable'",
                                            ),
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
                                    .properties(title=chart_title, height=320)
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
                                st.altair_chart(
                                    breakeven_chart + breakeven_rule, width="stretch"
                                )

                            if not econ_df.empty:
                                st.plotly_chart(
                                    _build_unit_economics_chart(econ_df),
                                    width="stretch",
                                )

                            if not breakeven_df.empty:
                                with st.expander(
                                    "Miner breakeven table...", expanded=False
                                ):
                                    price_map = {
                                        m.name: (m.price_usd or 0.0)
                                        * network_data.usd_to_gbp
                                        for m in miners_all
                                    }
                                    table_df = breakeven_df.copy()
                                    table_df["capex_gbp"] = table_df["miner"].map(
                                        price_map
                                    )
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
                                    table_df = table_df[display_cols].reset_index(
                                        drop=True
                                    )
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

                        include_non_viable = False

                        with st.expander("Miner payback analysis...", expanded=False):
                            st.markdown(
                                textwrap.dedent(
                                    """
                                    - Chart 2 gives “project economics at site scale”: how each surviving miner actually performs if you fill the AD site with them.
                                    """
                                )
                            )

                            include_non_viable = st.checkbox(
                                "Show non-viable miners (greyed)",
                                value=False,
                                key="payback_include_non_viable",
                            )

                            if not payback_df.empty:
                                rule_df = pd.DataFrame(
                                    {
                                        "power_price_gbp_per_kwh": [
                                            site_inputs.electricity_cost
                                        ]
                                    }
                                )
                                payback_chart_title = alt.TitleParams(
                                    "Payback period vs power price",
                                    subtitle=(
                                        "At your power price (red line), see how long each miner "
                                        "takes to recover its capital cost."
                                    ),
                                    subtitleColor="#6b7280",
                                    subtitleFontSize=11,
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
                                            "miner:N",
                                            legend=alt.Legend(title="Miner"),
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
                                    .properties(title=payback_chart_title, height=360)
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
                                st.altair_chart(
                                    payback_chart + payback_rule, width="stretch"
                                )

                                if not econ_df.empty:
                                    st.plotly_chart(
                                        _build_site_economics_chart(
                                            econ_df,
                                            include_non_viable=include_non_viable,
                                        ),
                                        width="stretch",
                                    )

                                with st.expander(
                                    "Miner payback table...", expanded=False
                                ):
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
                                        sel_prices_gbp = [
                                            p / 100 for p in selected_pence
                                        ]
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
                                        pivot = pivot.reindex(
                                            index=[m.name for m in miners_all]
                                        )

                                        col_order = [
                                            (p, f"{p:.1f}p") for p in selected_pence
                                        ]
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
                                                {
                                                    col: "{:.0f}"
                                                    for col in pivot.columns[1:]
                                                },
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
                            else:
                                st.info("No payback data available for current inputs.")

                        with st.expander("Miner unified analysis...", expanded=False):
                            st.markdown(
                                textwrap.dedent(
                                    """
                                    - Chart 3 then overlays a clear recommendation (fastest payback, strong margin, efficient) so the user doesn’t have to mentally combine those charts themselves.
                                    """
                                )
                            )

                            if not payback_df.empty and not breakeven_df.empty:
                                breakeven_map = {
                                    row["miner"]: row["breakeven_price_gbp_per_kwh"]
                                    for _, row in breakeven_df.iterrows()
                                }
                                site_price = site_inputs.electricity_cost
                                rule_df = pd.DataFrame(
                                    {"power_price_gbp_per_kwh": [site_price]}
                                )

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
                                            "miner:N",
                                            legend=alt.Legend(title="Miner"),
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
                                            "miner:N",
                                            legend=alt.Legend(title="Miner"),
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

                                if not econ_df.empty:
                                    rec_fig, _ = (
                                        _build_consolidated_recommendation_chart(
                                            econ_df,
                                            include_non_viable=include_non_viable,
                                            project_years=site_inputs.project_years,
                                        )
                                    )
                                    st.plotly_chart(rec_fig, width="stretch")

                                with st.expander(
                                    "Miner unified table...", expanded=False
                                ):
                                    site_payback = build_viability_summary(
                                        miners=miners_all,
                                        breakeven_map=breakeven_map,
                                        site_price_gbp_per_kwh=site_price,
                                        payback_points=payback_points,
                                    )
                                    summary_df = pd.DataFrame(site_payback)
                                    if not summary_df.empty:
                                        summary_df = summary_df.sort_values(
                                            by=[
                                                "Viable at site",
                                                "Breakeven price (p/kWh)",
                                            ],
                                            ascending=[False, False],
                                        )
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
                                        st.info(
                                            "Unified payback and breakeven details unavailable for current inputs."
                                        )
                            else:
                                st.info(
                                    "Unified payback details are unavailable for current inputs."
                                )

            st.markdown("---")
            st.markdown("## 3. Your financial forecasts")

            st.markdown(
                "These forecasts show how your selected revenue share applies across "
                "the base, best, and worst scenarios using your inputs."
            )
            st.caption(
                "We feed in the CapEx from your current miner plan so the payback and ROI "
                "figures line up with the site configuration above."
            )

            default_share_pct = int(
                settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE * 100
            )

            (
                placeholder_hashrate_key,
                placeholder_fee_key,
                difficulty_growth_pct,
                fee_growth_pct,
            ) = _get_forecast_growth_inputs()

            monthly_rows_for_scenarios = build_monthly_forecast(
                site=site_metrics,
                start_date=site_inputs.go_live_date,
                project_years=_derive_project_years(site_metrics),
                fee_growth_pct_per_year=float(fee_growth_pct),
                difficulty_growth_pct_per_year=float(difficulty_growth_pct),
            )

            def _coerce_share_pct(value):
                try:
                    return int(float(value))
                except (TypeError, ValueError):
                    return None

            client_share_candidates = [
                st.session_state.get("overview_client_share_pct"),
                st.session_state.get("scenario_client_share_pct"),
                st.session_state.get("pdf_scenarios", {}).get("client_share_pct"),
            ]
            client_share_pct = next(
                (
                    pct
                    for pct in (_coerce_share_pct(v) for v in client_share_candidates)
                    if pct is not None
                ),
                default_share_pct,
            )

            scenario_results = _build_scenario_results_snapshot(
                site_metrics=site_metrics,
                usd_to_gbp=network_data.usd_to_gbp,
                client_share_pct=client_share_pct,
                go_live_date=site_inputs.go_live_date,
                total_capex_gbp=getattr(capex_breakdown, "total_gbp", 0.0),
                monthly_rows=monthly_rows_for_scenarios,
            )

            if scenario_results:
                base_result, best_result, worst_result = scenario_results

                _render_scenario_comparison(
                    base_result=base_result,
                    best_result=best_result,
                    worst_result=worst_result,
                    heading="Scenario comparison table",
                )

                with st.expander("Scenario detailed analysis...", expanded=False):
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
                        total_capex_gbp=getattr(capex_breakdown, "total_gbp", 0.0),
                        monthly_rows=monthly_rows_for_scenarios,
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
    # LEARN TAB
    # ---------------------------------------------------------
    with tab_learn:
        render_learn_about_bitcoin()

    # ---------------------------------------------------------
    # ASSUMPTIONS TAB
    # ---------------------------------------------------------
    with tab_assumptions:
        render_assumptions_and_methodology()

    # ---------------------------------------------------------
    # FAQ TAB
    # ---------------------------------------------------------
    with tab_faq:
        st.markdown(
            textwrap.dedent(
                """
                # Choosing your ASIC – FAQ for AD plant operators

                This page explains how to use the dashboard to choose the right Bitcoin miner (ASIC) for **your** anaerobic digestion (AD) site.

                The questions below are written from an AD plant operator’s perspective and link directly to the charts in this app.

                ---

                ## 1. What is this tool actually helping me decide?

                **Question:**  
                > *“Which miner (or miners) should I install on my site to make the best use of my power and capital?”*

                The app does **not** force a single “best miner”.  
                Instead, it shows you how each miner performs against five key economic questions:

                1. Can this miner survive at **my** power price?  
                2. How much **daily profit per unit** does it make at my site?  
                3. How much **total site revenue** can I generate if I fill the site with this miner?  
                4. How **fast** does it pay back its capital cost?  
                5. How **sensitive** is it to changes in power price?

                You can then choose the miner that best matches your own priorities  
                (e.g. fastest payback, highest revenue, most efficient, lowest risk).

                ---

                ## 2. How do I read the *Breakeven power price per miner* chart?

                **Question:**  
                > *“Which miners can actually operate profitably at my power price?”*

                - Each dot is a miner.  
                - The x-axis shows the **breakeven power price** for that miner (£/kWh).  
                - The red dashed line shows **your** power price.  
                - Miners **to the right** of the red line are labelled **“Appropriate”** – they can make money at your power price.  
                - Miners **to the left** of the line are **“Not suitable”** – they need cheaper power than you have.

                **How to use it**

                1. Look at the red dashed line (your price).  
                2. Ignore any miners to the **left** of that line – they are not viable for this site.  
                3. Focus only on miners to the **right** – those pass the first filter.

                This answers: **“Who survives my power price?”**

                ---

                ## 3. How do I read the *Miner unit economics vs efficiency* chart?

                **Question:**  
                > *“For each miner that survives, how much money does one unit make per day?”*

                - X-axis: **Efficiency (J/TH)** – lower is better.  
                - Y-axis: **Daily gross margin per unit** (£/day) at your current power price.  
                - The dashed horizontal line is **breakeven** – above it is profit, below is loss.  
                - Hover over a point to see miner name, efficiency, daily profit, power draw and capex.

                **How to use it**

                1. Ignore miners that were “Not suitable” in the breakeven chart.  
                2. Among the remaining miners, look for points **above** the breakeven line.  
                3. Higher on the chart = more **daily profit per unit**.  
                4. Further left = more **efficient** (fewer joules per TH).

                This answers:  
                - **“Which miner makes the most per day at my site?”**  
                - **“How does that compare to its efficiency?”**

                ---

                ## 4. How do I read the *Payback period vs power price* chart?

                **Question:**  
                > *“How sensitive is each miner’s payback to electricity price?”*

                - Each line is a miner.  
                - X-axis: **power price** (£/kWh).  
                - Y-axis: **simple payback** (days).  
                - The red dashed line shows **your** power price.

                **How to use it**

                1. Find the vertical red line (your price).  
                2. Read off where each miner’s line crosses that point – that is its **payback at your price**.  
                3. Steeper lines are **more sensitive** – payback gets much worse as price increases.  
                4. Flatter lines are **more robust** to price changes.

                This answers:  
                - **“How long until I get my money back?”**  
                - **“Which miner is most at risk if my power cost rises?”**

                ---

                ## 5. How do I read the *Site-level economics by miner type* bubble chart?

                **Question:**  
                > *“If I fill my site with as many of this miner as the power allows, how does it perform overall?”*

                - X-axis: **Site gross margin (£/day)** – higher is better.  
                - Y-axis: **Payback (days)** – lower is better.  
                - Bubble size: **number of units** that fit in your site power.  
                - Bubble colour: **Efficiency (J/TH) — lower is better** (darker = more efficient).

                **How to use it**

                - **Bottom-right** is generally best: high site margin and fast payback.  
                - Big, dark bubbles near the bottom-right are:  
                  - Efficient  
                  - Profitable  
                  - Able to use a lot of your site power  

                This answers:  
                - **“Which miner makes the most money for the whole site?”**  
                - **“Which miner gives the fastest payback at the site level?”**

                ---

                ## 6. Why isn’t efficiency alone enough to pick a miner?

                It can be tempting to choose the miner with the **best efficiency (lowest J/TH)** and stop there.

                However, efficiency alone ignores:

                - **Hashrate** (how much work the miner does)  
                - **CapEx** (how much each miner costs to buy)  
                - **Power draw per unit** (how many miners you can actually fit on your site)  
                - **Sensitivity to power price** (how quickly profit disappears if tariffs change)

                Two common examples where efficiency is misleading:

                1. A very efficient miner with **low hashrate** may make less money per day than a slightly less efficient but much faster miner.  
                2. A very efficient miner with **high CapEx** might be slow to pay back, even though it looks great on paper.

                The charts in this app are designed to show when that happens.

                ---

                ## 7. What kinds of priorities might I have as an AD plant operator?

                Different sites and owners care about different things.  
                Typical priorities include:

                - **Maximise revenue** – “I want the highest site income per day.”  
                - **Fastest payback** – “I want my capital back as quickly as possible.”  
                - **Most efficient** – “I want to get the most BTC from each kWh.”  
                - **Robust to price changes** – “I want a miner that still works if my power price rises.”  
                - **Lowest capital requirement** – “I want a solution that fits my budget.”

                You can use the charts to find the miner that best matches your own priority, without having to state that priority explicitly in the tool.

                ---

                ## 8. What is *not* captured yet?

                The current version of the app focuses on **economic performance**:

                - Breakeven at your power price  
                - Daily unit economics  
                - Site-level economics  
                - Simple payback

                Future versions may also consider:

                - Noise and heat output  
                - Ease of repair and spare parts availability  
                - Expected resale value  
                - Network difficulty and halving scenarios  
                - More advanced metrics such as IRR

                For now, the app gives you a robust economic basis for choosing which miners to install on your AD site.
                """
            )
        )

    #    st.markdown("---")

    render_pdf_download_section()

    render_footer()


def _render_btc_monthly_forecast(
    site_metrics: SiteMetrics, site_inputs, network_data: NetworkData
) -> BTCForecastContext:
    (
        placeholder_hashrate_key,
        placeholder_fee_key,
        difficulty_growth_pct,
        fee_growth_pct,
    ) = _get_forecast_growth_inputs()

    ctx = BTCForecastContext(
        monthly_rows=[],
        monthly_df=pd.DataFrame(),
        fee_growth_pct=float(fee_growth_pct),
        difficulty_growth_pct=float(difficulty_growth_pct),
    )
    with st.expander("BTC forecast...", expanded=False):
        st.markdown(
            "This chart shows BTC mined per month (solid) and total BTC accumulated "
            "(dashed). The drop in 2028 is the block reward halving."
        )

        monthly_rows = build_monthly_forecast(
            site=site_metrics,
            start_date=site_inputs.go_live_date,
            project_years=_derive_project_years(site_metrics),
            fee_growth_pct_per_year=float(fee_growth_pct),
            difficulty_growth_pct_per_year=float(difficulty_growth_pct),
        )
        ctx.monthly_rows = monthly_rows
        monthly_df, y_domain, halving_dates = prepare_btc_display(
            monthly_rows,
            pad_pct=getattr(settings, "HISTOGRAM_Y_PAD_PCT", 0.3) or 0.0,
            next_halving=getattr(settings, "NEXT_HALVING_DATE", None),
            interval_years=int(getattr(settings, "HALVING_INTERVAL_YEARS", 4)),
        )
        ctx.monthly_df = monthly_df

        if monthly_df.empty:
            st.info("Monthly forecast unavailable for current inputs.")
            return ctx

        chart_df = monthly_df.rename(
            columns={"Month": "month", "BTC mined": "btc_mined_month"}
        ).copy()
        chart_df["month"] = pd.to_datetime(chart_df["month"])
        if halving_dates:
            halving_months = pd.to_datetime(halving_dates).to_period("M")
            chart_df["is_halving"] = (
                chart_df["month"].dt.to_period("M").isin(halving_months)
            )
            chart_df["halving_label"] = chart_df["month"].apply(
                lambda d: f"Halving – {d.strftime('%b %Y')}"
            )
        render_btc_forecast_chart(chart_df, title="BTC forecast")
        st.caption(
            "BTC forecast chart",
            help=(
                "Data is calculated monthly; the x-axis displays representative "
                "time points for readability."
            ),
        )

        with st.expander("BTC forecast diagnostics...", expanded=False):
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

        with st.expander("BTC forecast advanced...", expanded=False):
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
            placeholder_hashrate_growth = st.slider(
                "Hashrate growth (%/year)",
                min_value=0,
                max_value=100,
                value=int(difficulty_growth_pct),
                step=1,
                key=placeholder_hashrate_key,
                help="Placeholder slider mirroring the main hashrate growth control.",
            )
            placeholder_fee_growth = st.slider(
                "Fee growth (%/year)",
                min_value=0,
                max_value=100,
                value=int(fee_growth_pct),
                step=1,
                key=placeholder_fee_key,
                help="Placeholder slider mirroring the main fee growth control.",
            )
            fee_growth_pct = placeholder_fee_growth
            ctx.fee_growth_pct = float(placeholder_fee_growth)
            difficulty_growth_pct = placeholder_hashrate_growth
            ctx.difficulty_growth_pct = float(placeholder_hashrate_growth)

            display_df = monthly_df.rename(
                columns={
                    "BTC mined": "BTC mined (BTC)",
                    "Block reward": "Block reward (BTC)",
                    "Block subsidy": "Block subsidy (BTC)",
                }
            )
            st.dataframe(
                display_df.style.format(
                    {
                        "Month": _format_month,
                        "BTC mined (BTC)": "{:.5f}",
                        "Block reward (BTC)": "{:.6f}",
                        "Block subsidy (BTC)": "{:.4f}",
                        "Block Tx Fees (BTC)": "{:.6f}",
                    },
                    na_rep="—",
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
    with st.expander("Fiat forecast...", expanded=False):
        st.markdown(
            "This chart shows expected monthly revenue in GBP based on BTC mined per "
            "month and projected BTC price, along with electricity cost and BTC price "
            "path."
        )
        st.markdown(
            "This chart answers the question - What are my monthly economics in GBP "
            "(revenue, cost, profit)?"
        )
        price_growth_pct = st.session_state.get(
            "fiat_price_growth_pct",
            int(getattr(settings, "DEFAULT_BTC_PRICE_GROWTH_PCT", 0)),
        ) or int(getattr(settings, "DEFAULT_BTC_PRICE_GROWTH_PCT", 0))
        ctx.price_growth_pct = float(price_growth_pct)

        monthly_rows = btc_ctx.monthly_rows
        if not monthly_rows:
            fee_growth_pct_val = getattr(
                btc_ctx,
                "fee_growth_pct",
                getattr(settings, "DEFAULT_FEE_GROWTH_PCT", 0),
            )
            difficulty_growth_pct_val = getattr(
                btc_ctx,
                "difficulty_growth_pct",
                getattr(settings, "DEFAULT_HASHRATE_GROWTH_PCT", 0),
            )
            monthly_rows = build_monthly_forecast(
                site=site_metrics,
                start_date=site_inputs.go_live_date,
                project_years=_derive_project_years(site_metrics),
                fee_growth_pct_per_year=float(fee_growth_pct_val),
                difficulty_growth_pct_per_year=float(difficulty_growth_pct_val),
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
        fiat_df, y_domain, halving_dates = prepare_fiat_display(
            fiat_rows=fiat_rows,
            pad_pct=getattr(settings, "LINE_Y_PAD_PCT", 0.3) or 0.0,
            next_halving=getattr(settings, "NEXT_HALVING_DATE", None),
            interval_years=int(getattr(settings, "HALVING_INTERVAL_YEARS", 4)),
        )
        ctx.fiat_df = fiat_df

        if fiat_df.empty:
            st.info("Fiat forecast unavailable for current inputs.")
            return ctx

        chart_df = fiat_df.rename(
            columns={
                "Month": "month",
                "Revenue (GBP)": "revenue_gbp",
                "BTC price (USD)": "btc_price_usd",
            }
        ).copy()
        # Drop any duplicate columns (some upstream transforms may already carry a
        # lowercase month column) and normalise the month values.
        chart_df = chart_df.loc[:, ~chart_df.columns.duplicated()].copy()
        chart_df["month"] = pd.to_datetime(chart_df["month"], errors="coerce")
        # Add monthly power cost (GBP) if we have daily power cost from site metrics.
        if getattr(site_metrics, "site_power_cost_gbp_per_day", None) is not None:
            days_in_month = chart_df["month"].dt.to_period("M").dt.days_in_month
            chart_df["power_cost_gbp"] = (
                site_metrics.site_power_cost_gbp_per_day * days_in_month
            )
            if "revenue_gbp" in chart_df.columns:
                chart_df["net_cashflow_gbp"] = (
                    chart_df["revenue_gbp"] - chart_df["power_cost_gbp"]
                )
        else:
            if "revenue_gbp" in chart_df.columns and "net_cashflow_gbp" not in chart_df:
                chart_df["net_cashflow_gbp"] = chart_df["revenue_gbp"]
        halving_dates = halving_dates or []
        render_fiat_forecast_chart(
            chart_df,
            title="Fiat forecast",
            halving_dates=halving_dates,
        )

        capex = (
            st.session_state.get("pdf_capex_breakdown").total_gbp
            if st.session_state.get("pdf_capex_breakdown")
            else 0.0
        )
        if capex > 0 and "net_cashflow_gbp" in chart_df.columns:
            cash_df = chart_df[["month", "net_cashflow_gbp"]].dropna()
            payback_idx, payback_label = render_cumulative_cashflow_chart(
                cash_df,
                initial_capex_gbp=capex,
                title="Cumulative cashflow & payback",
            )
            metrics = compute_investment_metrics(cash_df, initial_capex_gbp=capex)
            render_investment_summary(
                metrics=metrics,
                initial_capex_gbp=capex,
                payback_month_index=payback_idx,
                payback_month_label=payback_label,
            )

        with st.expander("Fiat forecast advanced...", expanded=False):
            price_growth_pct = st.slider(
                "BTC price growth (%/year)",
                min_value=-100,
                max_value=200,
                value=int(price_growth_pct),
                step=1,
                key="fiat_price_growth_pct",
                help="Annual BTC price growth, applied monthly.",
            )
            ctx.price_growth_pct = float(price_growth_pct)
            display_cols = ["Month", "Revenue (GBP)", "BTC price (USD)", "BTC mined"]
            display_df = fiat_df[display_cols].copy()
            st.dataframe(
                display_df.style.format(
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

    unified_df = build_unified_monthly_table(
        monthly_df, fiat_df, usd_to_gbp=network_data.usd_to_gbp
    )

    with st.expander("Unified BTC & Fiat forecast...", expanded=False):
        st.markdown(
            "This chart answers the question - How does BTC mined × BTC price produce "
            "that revenue?"
        )
        chart_df = unified_df.rename(
            columns={
                "Month": "month",
                "BTC mined": "btc_mined",
                "Revenue (GBP)": "revenue_gbp",
                "BTC price (GBP)": "btc_price_gbp",
            }
        ).copy()
        chart_df["month"] = pd.to_datetime(chart_df["month"])
        halving_dates = build_halving_dates(
            getattr(settings, "NEXT_HALVING_DATE", None),
            int(getattr(settings, "HALVING_INTERVAL_YEARS", 4)),
            chart_df["month"].max().date(),
        )
        render_unified_forecast_chart(
            chart_df,
            title="Unified BTC & Fiat forecast",
            halving_dates=halving_dates,
        )
        with st.expander("Unified BTC & Fiat forecast advanced...", expanded=False):
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
    # Use a Streamlit component so our JS runs; markdown strips scripts.
    components.html(
        f"""
        <style>
        .pdf-section {{
            border-top: 1px solid #e5e7eb;
            padding: 6px 0 2px 0;
            margin: 10px 0 0 0;
            font-family: "Source Sans Pro", Arial, sans-serif;
            color: #111827;
        }}
        .pdf-heading {{
            margin: 0;
            font-size: 1.125rem;
            font-weight: 600;
        }}
        .pdf-row {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;
            min-height: 44px;
        }}
        .pdf-actions {{
            display: flex;
            gap: 0.5rem;
        }}
        .pdf-actions button {{
            background-color: #f3f4f6;
            color: #111827;
            border: 1px solid #d1d5db;
            border-radius: 0.375rem;
            padding: 0.45rem 0.95rem;
            font-weight: 600;
            cursor: pointer;
            min-width: 120px;
        }}
        .pdf-actions button:hover {{
            background-color: #e5e7eb;
        }}
        </style>
        <div class="pdf-section">
            <div class="pdf-row">
                <p class="pdf-heading">Your proposal for a 21Scot data centre</p>
                <div class="pdf-actions">
                    <button id="viewPdfBtn">View PDF</button>
                </div>
            </div>
        </div>
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
            document.getElementById('viewPdfBtn').onclick = () => {{
                const blobUrl = buildBlobUrl();
                window.open(blobUrl, '_blank');
                setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
            }};
        </script>
        """,
        height=80,
    )
