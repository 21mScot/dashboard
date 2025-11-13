# src/ui/scenarios.py

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from src.config import settings
from src.core.live_data import NetworkData
from src.ui.miner_selection import MinerOption
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


def _compute_num_miners(site: SiteInputs, miner: MinerOption) -> int:
    """How many miners can we fit into the available site power?"""
    # Base power draw in kW
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

    # miner hashrate in H/s
    miner_hashrate_hs = miner.hashrate_th * 1e12
    site_hashrate_hs = miner_hashrate_hs * num_miners

    # network hashrate: difficulty * 2^32 / 600 ≈ H/s
    network_hashrate_hs = network_difficulty * (2**32) / 600.0
    if network_hashrate_hs <= 0:
        return 0.0

    share_of_network = site_hashrate_hs / network_hashrate_hs
    blocks_per_day = 144

    btc_per_day_raw = share_of_network * block_subsidy_btc * blocks_per_day

    # Adjust for uptime
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

    # kWh per day
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

    Works at site level (not per ASIC), uses:
      - SiteInputs (power, uptime, tariffs, commercial model, dates)
      - Selected miner
      - Live network data if available; falls back to defaults otherwise.
    """
    st.markdown("### 3. Scenarios & risk")
    st.markdown(
        "Explore how changes in Bitcoin price, network competition and "
        "electricity cost affect site-level daily economics."
    )

    # ----------- baseline from live data or static defaults -----------
    if network_data is not None:
        base_price = network_data.btc_price_usd
        base_diff = network_data.difficulty
        base_subsidy = network_data.block_subsidy_btc
    else:
        base_price = settings.DEFAULT_BTC_PRICE_USD
        base_diff = settings.DEFAULT_DIFFICULTY
        base_subsidy = settings.DEFAULT_BLOCK_SUBSIDY_BTC

    col_controls, col_results = st.columns([1, 2])

    with col_controls:
        st.subheader("Scenario controls")

        btc_price_pct = st.slider(
            "Bitcoin price change (%)",
            min_value=-50,
            max_value=50,
            value=0,
            help=(
                "Apply an up/down shock to the current BTC price "
                "to explore upside and downside scenarios."
            ),
        )

        difficulty_pct = st.slider(
            "Network competition (%)",
            min_value=-30,
            max_value=50,
            value=0,
            help=(
                "Represents changes in overall network difficulty. "
                "Higher values mean more competition from other miners."
            ),
        )

        elec_cost_pct = st.slider(
            "Electricity cost change (%)",
            min_value=-50,
            max_value=50,
            value=0,
            help="Apply a change to your electricity cost per kWh.",
        )

        st.caption(
            "These are simple shocks around today's assumptions. "
            "Project duration and halving effects will be layered on later."
        )

    # Derived parameters for scenario
    scenario_price = base_price * (1 + btc_price_pct / 100.0)
    scenario_diff = base_diff * (1 + difficulty_pct / 100.0)
    scenario_elec_cost = site.electricity_cost * (1 + elec_cost_pct / 100.0)

    # Build baseline and scenario results
    baseline = _build_scenario_result(
        label="Baseline",
        site=site,
        miner=miner,
        btc_price_usd=base_price,
        network_difficulty=base_diff,
        block_subsidy_btc=base_subsidy,
        elec_cost_per_kwh=site.electricity_cost,
    )

    scenario = _build_scenario_result(
        label="Scenario",
        site=site,
        miner=miner,
        btc_price_usd=scenario_price,
        network_difficulty=scenario_diff,
        block_subsidy_btc=base_subsidy,
        elec_cost_per_kwh=scenario_elec_cost,
    )

    with col_results:
        st.subheader("Site-level daily economics")

        if baseline.num_miners == 0:
            st.warning(
                "Based on the current site power and miner choice, we can't "
                "fit any units. Increase site power or choose a smaller ASIC."
            )
            return

        col_top_a, col_top_b, col_top_c = st.columns(3)
        with col_top_a:
            st.metric("Miners installed", f"{baseline.num_miners}")
        with col_top_b:
            st.metric("Site hashrate", f"{baseline.site_hashrate_th:,.0f} TH/s")
        with col_top_c:
            delta_value = scenario.profit_per_day_fiat - baseline.profit_per_day_fiat

            st.metric(
                "Scenario profit / day",
                f"£{scenario.profit_per_day_fiat:,.2f}",
                delta=f"£{delta_value:,.2f} vs baseline",
            )

        # Tabular comparison
        df = pd.DataFrame(
            [
                {
                    "Scenario": baseline.label,
                    "BTC / day": baseline.btc_per_day,
                    "Revenue / day (£)": baseline.revenue_per_day_fiat,
                    "Opex / day (£)": baseline.opex_per_day_fiat,
                    "Profit / day (£)": baseline.profit_per_day_fiat,
                },
                {
                    "Scenario": scenario.label,
                    "BTC / day": scenario.btc_per_day,
                    "Revenue / day (£)": scenario.revenue_per_day_fiat,
                    "Opex / day (£)": scenario.opex_per_day_fiat,
                    "Profit / day (£)": scenario.profit_per_day_fiat,
                },
            ]
        )

        st.dataframe(
            df.style.format(
                {
                    "BTC / day": "{:.5f}",
                    "Revenue / day (£)": "£{:.2f}",
                    "Opex / day (£)": "£{:.2f}",
                    "Profit / day (£)": "£{:.2f}",
                }
            ),
            hide_index=True,
        )

        # Optional: quick bar chart for profit comparison
        chart_df = df.set_index("Scenario")[["Profit / day (£)"]]
        st.bar_chart(chart_df, height=260)
