# src/ui/scenarios.py

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from src.config import settings
from src.core.live_data import NetworkData
from src.ui.miner_selection import MinerOption
from src.ui.scenarios_tab import render_scenarios_tab
from src.ui.site_inputs import SiteInputs


@dataclass
class SiteScenarioResult:
    """Site-level economics for a single scenario (per day)."""

    label: str
    num_miners: int
    site_hashrate_th: float
    btc_per_day: float
    revenue_per_day_fiat: float
    opex_per_day_fiat: float
    profit_per_day_fiat: float


# ---------- helpers ----------


def scenario_slider(
    label: str,
    min_val: int,
    max_val: int,
    default: int,
    help_text: str,
) -> int:
    """Render a consistently styled slider for the Scenario Controls."""
    st.markdown("<div style='margin-bottom: 1rem;'>", unsafe_allow_html=True)
    value = st.slider(
        label,
        min_value=min_val,
        max_value=max_val,
        value=default,
        help=help_text,
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return value


def _compute_num_miners(site: SiteInputs, miner: MinerOption) -> int:
    """How many miners can we fit into the available site power?"""
    miner_power_kw = miner.power_w / 1000.0
    overhead_factor = 1 + site.cooling_overhead_pct / 100.0

    effective_power_per_miner_kw = miner_power_kw * overhead_factor
    if effective_power_per_miner_kw <= 0:
        return 0

    num_miners = int(site.site_power_kw // effective_power_per_miner_kw)
    return max(num_miners, 0)


def _estimate_btc_per_day_site(
    site: SiteInputs,
    miner: MinerOption,
    network_difficulty: float,
    block_subsidy_btc: float,
) -> float:
    """Expected BTC/day for the whole site, given difficulty."""
    num_miners = _compute_num_miners(site, miner)
    if num_miners <= 0:
        return 0.0

    miner_hashrate_hs = miner.hashrate_th * 1e12
    site_hashrate_hs = miner_hashrate_hs * num_miners

    # network hashrate: difficulty * 2^32 / 600 ≈ H/s
    network_hashrate_hs = network_difficulty * (2**32) / 600.0
    if network_hashrate_hs <= 0:
        return 0.0

    share_of_network = site_hashrate_hs / network_hashrate_hs
    blocks_per_day = 144

    btc_per_day_raw = share_of_network * block_subsidy_btc * blocks_per_day

    uptime_factor = site.uptime_pct / 100.0
    return btc_per_day_raw * uptime_factor


def _estimate_site_opex_per_day(
    site: SiteInputs,
    miner: MinerOption,
    elec_cost_per_kwh: float,
) -> float:
    """Electricity + cooling cost per day for the site."""
    num_miners = _compute_num_miners(site, miner)
    if num_miners <= 0:
        return 0.0

    miner_power_kw = miner.power_w / 1000.0
    overhead_factor = 1 + site.cooling_overhead_pct / 100.0
    total_power_kw = num_miners * miner_power_kw * overhead_factor

    uptime_factor = site.uptime_pct / 100.0
    kwh_per_day = total_power_kw * 24.0 * uptime_factor

    return kwh_per_day * elec_cost_per_kwh


def _build_scenario_result(
    label: str,
    site: SiteInputs,
    miner: MinerOption,
    btc_price_usd: float,
    network_difficulty: float,
    block_subsidy_btc: float,
    elec_cost_per_kwh: float,
    fx_rate_usd_to_gbp: float = 0.8,  # simple constant for now
) -> SiteScenarioResult:
    num_miners = _compute_num_miners(site, miner)
    site_hashrate_th = num_miners * miner.hashrate_th

    btc_per_day = _estimate_btc_per_day_site(
        site=site,
        miner=miner,
        network_difficulty=network_difficulty,
        block_subsidy_btc=block_subsidy_btc,
    )

    revenue_per_day_usd = btc_per_day * btc_price_usd
    revenue_per_day_gbp = revenue_per_day_usd * fx_rate_usd_to_gbp

    opex_per_day_gbp = _estimate_site_opex_per_day(
        site=site,
        miner=miner,
        elec_cost_per_kwh=elec_cost_per_kwh,
    )

    profit_per_day_gbp = revenue_per_day_gbp - opex_per_day_gbp

    return SiteScenarioResult(
        label=label,
        num_miners=num_miners,
        site_hashrate_th=site_hashrate_th,
        btc_per_day=btc_per_day,
        revenue_per_day_fiat=revenue_per_day_gbp,
        opex_per_day_fiat=opex_per_day_gbp,
        profit_per_day_fiat=profit_per_day_gbp,
    )


# ---------- main UI ----------


def render_scenarios_and_risk(
    site: SiteInputs,
    miner: MinerOption,
    network_data: NetworkData | None,
) -> None:
    """Render the Scenarios & Risk tab.

    Left: simple daily shock controls (sliders).
    Right: Multi-year Scenario 1 (MVP) annual economics.
    """
    st.markdown("### 3. Scenarios & risk")
    st.markdown(
        "Explore how changes in Bitcoin price, network competition and "
        "electricity cost affect site-level economics."
    )

    # ----------- baseline from live data or static defaults -----------
    if network_data is not None:
        base_price = network_data.btc_price_usd
        base_diff = network_data.difficulty
        base_subsidy = network_data.block_subsidy_btc
    else:
        base_price = settings.DEFAULT_BTC_PRICE_USD
        base_diff = settings.DEFAULT_NETWORK_DIFFICULTY
        base_subsidy = settings.DEFAULT_BLOCK_SUBSIDY_BTC

    col_controls, col_results = st.columns([1, 4])

    # ----------- controls (left) -----------
    with col_controls:
        st.subheader("Scenario controls")

        btc_price_pct = scenario_slider(
            "Bitcoin price change (%)",
            -50,
            50,
            0,
            (
                "Apply an up/down shock to the current BTC price "
                "to explore upside and downside scenarios."
            ),
        )

        difficulty_pct = scenario_slider(
            "Network competition (%)",
            -30,
            50,
            0,
            (
                "Represents changes in overall network difficulty. "
                "Higher values mean more competition from other miners."
            ),
        )

        elec_cost_pct = scenario_slider(
            "Electricity cost change (%)",
            -50,
            50,
            0,
            "Apply a change to your electricity cost per kWh.",
        )

        st.caption(
            "These are simple shocks around today's assumptions. "
            "Project duration and halving effects will be layered on later."
        )

    # ----------- derived parameters for scenario -----------
    scenario_price = base_price * (1 + btc_price_pct / 100.0)
    scenario_diff = base_diff * (1 + difficulty_pct / 100.0)
    scenario_elec_cost = site.electricity_cost * (1 + elec_cost_pct / 100.0)

    # We still compute baseline + scenario in case we need them later,
    # but we don't currently show the daily table in the UI.
    _ = _build_scenario_result(
        label="Baseline",
        site=site,
        miner=miner,
        btc_price_usd=base_price,
        network_difficulty=base_diff,
        block_subsidy_btc=base_subsidy,
        elec_cost_per_kwh=site.electricity_cost,
    )

    _ = _build_scenario_result(
        label="Scenario",
        site=site,
        miner=miner,
        btc_price_usd=scenario_price,
        network_difficulty=scenario_diff,
        block_subsidy_btc=base_subsidy,
        elec_cost_per_kwh=scenario_elec_cost,
    )

    # ----------- Multi-year scenario (right) -----------
    with col_results:
        st.subheader("Multi-year Scenario 1 (MVP)")
        st.caption(
            "Annual site-level economics based on Scenario 1 assumptions. "
            "Sliders will influence this view in a later phase."
        )
        render_scenarios_tab()
