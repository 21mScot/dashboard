# src/ui/layout.py
from __future__ import annotations

import base64
import textwrap
from datetime import datetime, timezone

import streamlit as st

from src.config import settings
from src.config.settings import LIVE_DATA_CACHE_TTL_S
from src.config.version import APP_VERSION, PRIVACY_URL, TERMS_URL
from src.core.capex import compute_capex_breakdown
from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.core.scenario_calculations import build_base_annual_from_site_metrics
from src.core.scenario_config import build_default_scenarios
from src.core.scenario_engine import run_scenario
from src.core.site_metrics import SiteMetrics, compute_site_metrics
from src.ui.assumptions import render_assumptions_and_methodology
from src.ui.miner_selection import get_default_miner, load_miner_options
from src.ui.pdf_export import build_pdf_report
from src.ui.scenario_1 import render_scenario_panel
from src.ui.scenarios import (
    _build_dummy_base_years,
    _derive_project_years,
    _render_scenario_comparison,
    render_scenarios_and_risk,
)
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
        usd_to_gbp_rate=network_data.usd_to_gbp,
    )


# ---------------------------------------------------------
# Helper: run scenarios for snapshot view
# ---------------------------------------------------------
def _build_scenario_results_snapshot(
    site_metrics: SiteMetrics,
    usd_to_gbp: float,
    client_share_pct: float,
):
    project_years = _derive_project_years(site_metrics)

    if isinstance(site_metrics, SiteMetrics) and site_metrics.asics_supported > 0:
        base_years = build_base_annual_from_site_metrics(
            site=site_metrics,
            project_years=project_years,
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
        st.markdown("## 1. Set up your site parameters")

        # Miner selection (default or from prior choice)
        miner_options = list(load_miner_options())
        miner_by_name = {m.name: m for m in miner_options}
        default_miner = get_default_miner()
        selected_miner_name = (
            st.session_state.get("selected_miner_name") or default_miner.name
        )
        selected_miner = miner_by_name.get(selected_miner_name, default_miner)
        st.session_state["selected_miner_name"] = selected_miner.name

        # Inputs + timeline
        site_inputs = render_site_inputs()

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

        st.markdown("---")
        st.markdown("## 2. Your site daily performance")
        st.markdown(
            "We've calculated these values with today's network data and hardware "
            "that's available, so they provide an accurate snapshot of your site's "
            "potential."
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
                "Net income / day",
                f"£{site_metrics.site_net_revenue_gbp_per_day:,.0f}",
                help=(
                    "Gross revenue minus electricity cost for all ASICs on site, "
                    "after applying your uptime assumption. This is the net income "
                    "the site generates per day before tax and other overheads."
                ),
            )
        with metrics_col2:
            st.metric(
                "Net income per kWh",
                f"£{site_metrics.net_revenue_per_kwh_gbp:,.3f}",
                help=(
                    "Net income divided by the kWh of energy actually used per day. "
                    "Shows the economic value (£/kWh) of routing your energy into "
                    "Bitcoin mining instead of alternative uses."
                ),
            )
        with metrics_col3:
            st.metric(
                "BTC mined / day",
                f"{site_metrics.site_btc_per_day:.5f} BTC",
                help=(
                    "Total BTC expected per day from all ASICs at the configured "
                    "uptime, using the current network difficulty and block subsidy."
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
                        "Gross revenue minus electricity cost for all ASICs on site, "
                        "after applying your uptime assumption. This is the net "
                        "income the site generates per day before tax and other "
                        "overheads."
                    ),
                )
            with f2:
                st.metric(
                    "Gross revenue / day",
                    f"£{site_metrics.site_revenue_gbp_per_day:,.0f} ("
                    f"${site_metrics.site_revenue_usd_per_day:,.0f})",
                    help=(
                        "Expected revenue for one ASIC (based on BTC price, "
                        "difficulty, and block reward), multiplied by the number of "
                        "ASICs running, adjusted for uptime, and converted from USD "
                        "to GBP using the FX rate in the sidebar."
                    ),
                )
            with f3:
                st.metric(
                    "Electricity cost / day",
                    f"£{site_metrics.site_power_cost_gbp_per_day:,.0f}",
                    help=(
                        "Estimated electricity spend per day for running all ASICs, "
                        "including cooling/overhead power. Based on site kWh usage, "
                        "your electricity tariff (£/kWh), and uptime."
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
                        "Total electrical load drawn by all ASICs, including cooling "
                        "and overhead. This is the kW actually committed to mining "
                        "when the site is fully running."
                    ),
                )
            with u3:
                st.metric(
                    "Power per ASIC (incl. overhead)",
                    f"{site_metrics.power_per_asic_kw:.2f} kW",
                    help=(
                        "Effective kW per ASIC including cooling/overhead. Calculated "
                        "from the miner nameplate power plus the cooling/overhead "
                        "percentage set in the inputs."
                    ),
                )

            # Row 3 — Efficiency & scale
            e1, e2, e3 = st.columns(3)
            with e1:
                st.metric(
                    "Net income per kWh",
                    f"£{site_metrics.net_revenue_per_kwh_gbp:,.3f}",
                    help=(
                        "Net income divided by the kWh of energy actually used per "
                        "day. Shows the economic value (£/kWh) of routing your energy "
                        "into Bitcoin mining instead of alternative uses."
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
                        "Total BTC expected per day from all ASICs at the configured "
                        "uptime, using the current network difficulty and block "
                        "subsidy."
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

                sorted_options = sorted(
                    miner_options, key=lambda m: m.hashrate_th, reverse=True
                )
                option_labels = [
                    f"{m.name} — {m.hashrate_th:.0f} TH/s" for m in sorted_options
                ]
                label_to_name = {
                    f"{m.name} — {m.hashrate_th:.0f} TH/s": m.name
                    for m in sorted_options
                }
                current_label = next(
                    (
                        lbl
                        for lbl in option_labels
                        if label_to_name[lbl] == selected_miner.name
                    ),
                    option_labels[0],
                )
                selected_label = st.selectbox(
                    "Alternative ASIC miners",
                    options=option_labels,
                    index=option_labels.index(current_label),
                    key="selected_miner_label",
                    help="Select from currently available miners.",
                )
                if selected_label != current_label:
                    st.session_state["selected_miner_name"] = label_to_name[
                        selected_label
                    ]
                    # Trigger rerun for immediate update across sections
                    rerun_fn = getattr(st, "rerun", None) or getattr(
                        st, "experimental_rerun", None
                    )
                    if rerun_fn:
                        rerun_fn()

        st.markdown("---")
        st.markdown("## 3. Your financial forecasts")

        st.markdown(
            "These forecasts show how your selected revenue share applies across the "
            "base, best, and worst scenarios using your inputs."
        )

        default_share_pct = int(settings.SCENARIO_DEFAULT_CLIENT_REVENUE_SHARE * 100)
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

        st.markdown("---")

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

    render_pdf_download_section()
    render_footer()


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
