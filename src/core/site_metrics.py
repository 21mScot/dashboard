# src/core/site_metrics.py
from __future__ import annotations

from dataclasses import dataclass
from math import floor

from src.config import settings
from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics
from src.core.miner_models import MinerOption

FX_USD_TO_GBP_DEFAULT = 0.8  # tweak as needed


@dataclass
class SiteMetrics:
    # Capacity
    asics_supported: int
    power_per_asic_kw: float  # incl. cooling/overhead
    site_power_used_kw: float
    site_power_available_kw: float
    spare_capacity_kw: float

    # Economics (per day)
    site_btc_per_day: float
    site_revenue_usd_per_day: float
    site_revenue_gbp_per_day: float
    site_power_cost_gbp_per_day: float
    site_net_revenue_gbp_per_day: float

    # Efficiency (per day)
    net_revenue_per_kw_gbp_per_day: float
    net_revenue_per_kwh_gbp: float

    @classmethod
    def from_calibration(
        cls,
        miner_ths: float,
        miner_kw: float,
        start_difficulty: float,
        start_btc_price_usd: float | None = None,
        tx_fee_btc_per_block: float | None = None,
        pool_fee_pct: float = 0.0,
        uptime_pct: float = 100.0,
        electricity_usd_per_kwh: float = 0.0,
        additional_opex_usd_per_month: float = 0.0,
        usd_to_gbp: float | None = None,
    ) -> "SiteMetrics":
        """
        Build a minimal SiteMetrics snapshot directly from hash rate,
        power draw, difficulty, and basic economic assumptions. This is
        useful for aligning against external calculators (e.g., Braiins).
        """
        btc_price_usd = (
            float(start_btc_price_usd)
            if start_btc_price_usd is not None
            else float(getattr(settings, "DEFAULT_BTC_PRICE_USD", 0.0))
        )
        fee_per_block = (
            float(tx_fee_btc_per_block)
            if tx_fee_btc_per_block is not None
            else float(getattr(settings, "DEFAULT_FEE_BTC_PER_BLOCK", 0.0))
        )
        usd_to_gbp_rate = (
            float(usd_to_gbp)
            if usd_to_gbp is not None
            else float(getattr(settings, "DEFAULT_USD_TO_GBP", 0.75))
        )

        pool_fee_fraction = max(0.0, pool_fee_pct) / 100.0
        uptime_factor = max(0.0, min(uptime_pct, 100.0)) / 100.0

        # Network hashrate derived from difficulty (H/s)
        seconds_per_block = 600.0  # Bitcoin target block time
        network_hashrate_hs = (
            float(start_difficulty) * (2**32) / seconds_per_block
            if start_difficulty > 0
            else 0.0
        )
        miner_hashrate_hs = max(0.0, miner_ths) * 1e12
        share = (
            miner_hashrate_hs / network_hashrate_hs if network_hashrate_hs > 0 else 0.0
        )

        reward_btc_per_block = (
            float(getattr(settings, "DEFAULT_BLOCK_SUBSIDY_BTC", 0.0)) + fee_per_block
        )
        blocks_per_day = 86400.0 / seconds_per_block

        btc_per_day = (
            share
            * blocks_per_day
            * reward_btc_per_block
            * (1.0 - pool_fee_fraction)
            * uptime_factor
        )
        revenue_usd_per_day = btc_per_day * btc_price_usd
        revenue_gbp_per_day = revenue_usd_per_day * usd_to_gbp_rate

        # Simple power cost model (GBP/day)
        power_cost_gbp_per_day = (
            max(0.0, miner_kw) * 24.0 * uptime_factor * electricity_usd_per_kwh
        ) * usd_to_gbp_rate
        other_opex_gbp_per_day = (
            max(0.0, additional_opex_usd_per_month) / 30.0
        ) * usd_to_gbp_rate

        net_revenue_gbp_per_day = (
            revenue_gbp_per_day - power_cost_gbp_per_day - other_opex_gbp_per_day
        )

        power_used_kw = max(0.0, miner_kw) * uptime_factor
        kwh_per_day = power_used_kw * 24.0

        net_revenue_per_kw_gbp_per_day = (
            net_revenue_gbp_per_day / power_used_kw if power_used_kw > 0 else 0.0
        )
        net_revenue_per_kwh_gbp = (
            net_revenue_gbp_per_day / kwh_per_day if kwh_per_day > 0 else 0.0
        )

        return cls(
            asics_supported=1,
            power_per_asic_kw=max(0.0, miner_kw),
            site_power_used_kw=power_used_kw,
            site_power_available_kw=max(0.0, miner_kw),
            spare_capacity_kw=max(0.0, miner_kw - power_used_kw),
            site_btc_per_day=btc_per_day,
            site_revenue_usd_per_day=revenue_usd_per_day,
            site_revenue_gbp_per_day=revenue_gbp_per_day,
            site_power_cost_gbp_per_day=power_cost_gbp_per_day,
            site_net_revenue_gbp_per_day=net_revenue_gbp_per_day,
            net_revenue_per_kw_gbp_per_day=net_revenue_per_kw_gbp_per_day,
            net_revenue_per_kwh_gbp=net_revenue_per_kwh_gbp,
        )


def compute_site_metrics(
    miner: MinerOption,
    network: NetworkData,
    site_power_kw: float,
    electricity_cost_per_kwh_gbp: float,
    uptime_pct: float,
    cooling_overhead_pct: float,
    usd_to_gbp_rate: float = FX_USD_TO_GBP_DEFAULT,
) -> SiteMetrics:
    """
    Scale from a single miner to a whole site, given a site power limit
    and electricity cost.

    - miner: selected MinerOption
    - network: NetworkData snapshot (can be static or live)
    - site_power_kw: available site power capacity in kW
    - electricity_cost_per_kwh_gbp: £/kWh
    - uptime_pct: expected uptime as a percentage (e.g. 98 for 98%)
    - cooling_overhead_pct: % overhead applied to miner power draw
    - usd_to_gbp_rate: FX rate used to convert USD revenues to GBP

    Returns a SiteMetrics object suitable for UI display.
    """
    # Guard against weird inputs
    if site_power_kw <= 0 or miner.power_w <= 0:
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

    uptime_factor = max(0.0, min(uptime_pct, 100.0)) / 100.0
    overhead_factor = 1.0 + max(0.0, cooling_overhead_pct) / 100.0

    miner_power_kw = miner.power_w / 1000.0
    power_per_asic_kw = miner_power_kw * overhead_factor

    if power_per_asic_kw <= 0:
        asics_supported = 0
    else:
        asics_supported = max(0, floor(site_power_kw / power_per_asic_kw))

    site_power_used_kw = asics_supported * power_per_asic_kw
    spare_capacity_kw = max(0.0, site_power_kw - site_power_used_kw)

    # Per-miner economics (already validated vs WhatToMine)
    econ = compute_miner_economics(miner.hashrate_th, network)
    btc_per_day_miner = econ.btc_per_day
    usd_per_day_miner = econ.revenue_usd_per_day

    site_btc_per_day = asics_supported * btc_per_day_miner * uptime_factor
    site_revenue_usd_per_day = asics_supported * usd_per_day_miner * uptime_factor
    site_revenue_gbp_per_day = site_revenue_usd_per_day * usd_to_gbp_rate

    # Power cost
    site_kwh_per_day = site_power_used_kw * 24.0 * uptime_factor
    site_power_cost_gbp_per_day = site_kwh_per_day * electricity_cost_per_kwh_gbp

    site_net_revenue_gbp_per_day = (
        site_revenue_gbp_per_day - site_power_cost_gbp_per_day
    )

    # Efficiency per kW of capacity actually used
    if site_power_used_kw > 0:
        net_revenue_per_kw_gbp_per_day = (
            site_net_revenue_gbp_per_day / site_power_used_kw
        )
    else:
        net_revenue_per_kw_gbp_per_day = 0.0

    # Efficiency per kWh of energy actually used
    if site_kwh_per_day > 0:
        net_revenue_per_kwh_gbp = site_net_revenue_gbp_per_day / site_kwh_per_day
    else:
        net_revenue_per_kwh_gbp = 0.0

    return SiteMetrics(
        asics_supported=asics_supported,
        power_per_asic_kw=power_per_asic_kw,
        site_power_used_kw=site_power_used_kw,
        site_power_available_kw=site_power_kw,
        spare_capacity_kw=spare_capacity_kw,
        site_btc_per_day=site_btc_per_day,
        site_revenue_usd_per_day=site_revenue_usd_per_day,
        site_revenue_gbp_per_day=site_revenue_gbp_per_day,
        site_power_cost_gbp_per_day=site_power_cost_gbp_per_day,
        site_net_revenue_gbp_per_day=site_net_revenue_gbp_per_day,
        net_revenue_per_kw_gbp_per_day=net_revenue_per_kw_gbp_per_day,
        net_revenue_per_kwh_gbp=net_revenue_per_kwh_gbp,
    )
