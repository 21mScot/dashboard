# src/core/miner_economics.py

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.core.live_data import NetworkData


@dataclass
class MinerEconomics:
    btc_per_day: float
    revenue_usd_per_day: float


def compute_miner_economics(hashrate_th: float, network: NetworkData) -> MinerEconomics:
    """
    Canonical calculation for BTC/day and USD/day for a single miner.

    - hashrate_th: miner hashrate in TH/s
    - network: NetworkData with difficulty, block_subsidy_btc, btc_price_usd

    Assumes:
    - 144 blocks per day
    - No pool fees
    - 100% uptime

    - Grok, how to derrive Hashprice:
    - daily_blocks = 144
    - block_subsidy = 3.125  # BTC post-2024 halving
    - total_daily_subsidy_btc = daily_blocks * block_subsidy
    - daily_fees_btc = fetch_from_api()  # e.g. mempool.space or blockchair
    - total_daily_revenue_btc = total_daily_subsidy_btc + daily_fees_btc
    - network_hashrate_eh = 1.00  # current ≈1 EH/s = 1,000,000 PH/s
    - hashprice_usd_per_ph_day = (total_daily_revenue_btc * btc_price_usd) /
      (network_hashrate_eh * 1_000_000)
    - or alternatively:
    - hashprice_usd_per_th_day = hashprice_usd_per_ph_day / 1_000
    - miner_revenue_usd_per_day = miner_hashrate_th * hashprice_usd_per_th_day
    - BTC per PH/s per day ≈ hashprice_USD / current_BTC_price

    # Option 1 – Direct from Luxor (industry standard)
    - import requests
      hashprice = requests.get(
          "https://api.hashrateindex.com/api/v1/public/hashprice"
      ).json()["usd"]

    # Option 2 – Derive from mempool.space (fully open-source)
      import requests
      hr = (
          requests.get("https://mempool.space/api/v1/mining/hashrate/24h")
          .json()["currentHashrate"]
          / 1e18
      )  # EH/s
      revenue = requests.get(
          "https://mempool.space/api/v1/mining/revenue/1d"
      ).json()["totalRevenue"]
      btc_price = requests.get(
          "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
      ).json()["bitcoin"]["usd"]
      hashprice = (revenue * btc_price) / (hr * 1e6)  # → USD per PH/s per day
    """
    hashrate_hs = hashrate_th * 1e12  # TH/s -> H/s
    difficulty = float(network.difficulty)
    block_subsidy = float(network.block_subsidy_btc)
    btc_price = float(network.btc_price_usd)

    if difficulty <= 0 or block_subsidy <= 0:
        return MinerEconomics(btc_per_day=0.0, revenue_usd_per_day=0.0)

    blocks_per_day = 144
    network_hashrate_hs = difficulty * 2**32 / 600  # H/s

    share = hashrate_hs / network_hashrate_hs
    btc_day = share * block_subsidy * blocks_per_day
    usd_day = btc_day * btc_price

    return MinerEconomics(btc_per_day=btc_day, revenue_usd_per_day=usd_day)


def compute_miner_economics_table(
    miners_df: pd.DataFrame,
    site_power_kw: float,
    elec_price_gbp_per_kwh: float,
    uptime_factor: float,
    btc_revenue_gbp_per_ths_per_day: float,
) -> pd.DataFrame:
    """
    Enrich miners_df with per-unit and site-level economics using site inputs.
    """
    df = miners_df.copy()

    # Capacity view: use full nameplate count; uptime is applied to revenue/cost,
    # not capacity.
    df["max_units_by_power"] = np.floor(site_power_kw / df["power_kw"]).astype(int)

    df["revenue_gbp_per_unit_per_day"] = (
        df["hashrate_ths"] * btc_revenue_gbp_per_ths_per_day * uptime_factor
    )

    df["elec_cost_gbp_per_unit_per_day"] = (
        df["power_kw"] * 24 * elec_price_gbp_per_kwh * uptime_factor
    )

    df["margin_gbp_per_unit_per_day"] = (
        df["revenue_gbp_per_unit_per_day"] - df["elec_cost_gbp_per_unit_per_day"]
    )

    df["is_viable"] = df["margin_gbp_per_unit_per_day"] > 0

    df["site_daily_margin_gbp"] = (
        df["margin_gbp_per_unit_per_day"] * df["max_units_by_power"]
    )

    df["site_capex_gbp"] = df["capex_gbp"] * df["max_units_by_power"]

    df["payback_days"] = np.where(
        (df["site_daily_margin_gbp"] > 0) & (df["site_capex_gbp"] > 0),
        df["site_capex_gbp"] / df["site_daily_margin_gbp"],
        np.nan,
    )

    return df


def select_recommended_miner(df: pd.DataFrame, project_years: int):
    """
    Pick the best miner based on viability, payback within project horizon,
    then lowest payback, highest margin, and best efficiency.
    """
    project_days = project_years * 365

    candidates = df[
        (df["is_viable"])
        & (df["max_units_by_power"] > 0)
        & df["payback_days"].notna()
        & (df["payback_days"] <= project_days)
    ].copy()

    if candidates.empty:
        candidates = df[
            (df["is_viable"])
            & (df["max_units_by_power"] > 0)
            & df["payback_days"].notna()
        ].copy()

    if candidates.empty:
        return None

    candidates = candidates.sort_values(
        by=["payback_days", "site_daily_margin_gbp", "efficiency_j_per_th"],
        ascending=[True, False, True],
    )

    return candidates.iloc[0]
