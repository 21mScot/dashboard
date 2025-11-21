# scripts/compare_external.py
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.config import settings
from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Miner specs for external comparison (hashrate in TH/s, power in W)
MINERS = {
    "Whatsminer M63S++ (480 TH/s)": {"hashrate_th": 480, "power_w": 7200},
    "Whatsminer M33S (240 TH/s)": {"hashrate_th": 240, "power_w": 7260},
    "Antminer S21 (200 TH/s)": {"hashrate_th": 200, "power_w": 3500},
    "Whatsminer M60 (186 TH/s)": {"hashrate_th": 186, "power_w": 3425},
    "Antminer S19k Pro (120 TH/s)": {"hashrate_th": 120, "power_w": 2760},
}


def print_economics(
    label: str, price_usd: float, difficulty: float, subsidy_btc: float
):
    """
    Print BTC/day and USD/day for all configured miners under a given
    network snapshot. This is intended for manual comparison against
    external calculators such as WhatToMine.
    """
    network = NetworkData(
        btc_price_usd=price_usd,
        difficulty=difficulty,
        block_subsidy_btc=subsidy_btc,
        block_height=None,
        usd_to_gbp=settings.DEFAULT_USD_TO_GBP,
        as_of_utc=datetime.now(timezone.utc),
        hashprice_usd_per_ph_day=None,
        hashprice_as_of_utc=None,
    )

    print(f"\n=== {label} ===")
    print(
        f"BTC price: {price_usd:,.2f}  |  "
        f"Difficulty: {difficulty:,.0f}  |  "
        f"Subsidy: {subsidy_btc} BTC"
    )
    print("-" * 110)
    print(
        f"{'Miner':32}  {'TH/s':>6}  {'Power (W)':>10}  "
        f"{'BTC/day':>12}  {'USD/day':>12}"
    )
    print("-" * 110)

    # Sort miners by hashrate (TH/s), descending
    sorted_miners = sorted(
        MINERS.items(),
        key=lambda x: x[1]["hashrate_th"],
        reverse=True,
    )

    for name, spec in sorted_miners:
        h_th = spec["hashrate_th"]
        power_w = spec["power_w"]

        econ = compute_miner_economics(h_th, network)
        print(
            f"{name:32}  {h_th:6.0f}  {power_w:10.0f}  "
            f"{econ.btc_per_day:12.8f}  "
            f"${econ.revenue_usd_per_day:11.2f}"
        )


if __name__ == "__main__":
    # Snapshot aligned with src/config/settings.py defaults
    print_economics(
        "21mScot static snapshot",
        price_usd=settings.DEFAULT_BTC_PRICE_USD,
        difficulty=settings.DEFAULT_NETWORK_DIFFICULTY,
        subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
    )
