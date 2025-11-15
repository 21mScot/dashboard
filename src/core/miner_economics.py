# src/core/miner_economics.py

from dataclasses import dataclass

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
