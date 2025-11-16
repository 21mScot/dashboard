# scripts/compare_external.py

import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics

MINERS = {
    "Antminer S21 (200 TH/s)": 200,
    "Whatsminer M60 (186 TH/s)": 186,
    "Antminer S19k Pro (120 TH/s)": 120,
}


def print_economics(label: str, price: float, difficulty: float, subsidy: float):
    network = NetworkData(
        btc_price_usd=price,
        difficulty=difficulty,
        block_subsidy_btc=subsidy,
        block_height=None,
    )

    print(f"\n=== {label} ===")
    print(
        f"BTC price: {price:,.2f}  |  Difficulty: {difficulty:,.0f}  |  Subsidy: {subsidy}"
    )
    for name, h_th in MINERS.items():
        econ = compute_miner_economics(h_th, network)
        print(
            f"{name:28}  BTC/day={econ.btc_per_day:.8f}  "
            f"USD/day=${econ.revenue_usd_per_day:,.2f}"
        )


if __name__ == "__main__":
    # example using your current static snapshot
    print_economics(
        "21mScot static snapshot",
        price=90_000,
        difficulty=150_000_000_000_000,
        subsidy=3.125,
    )
