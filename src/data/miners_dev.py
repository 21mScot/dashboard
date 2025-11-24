# src/data/miners_dev.py
from __future__ import annotations

from typing import Dict

from src.core.miner_models import MinerOption

# Dev-only catalogue: intentionally varied to exercise efficiency, breakeven,
# and payback behaviours when running locally.
MINERS: Dict[str, MinerOption] = {
    "TestMake A-Hyper-efficient (110 TH/s)": MinerOption(
        name="TestMake A-Hyper-efficient",
        hashrate_th=110.0,
        power_w=1650,
        efficiency_j_per_th=15.0,
        supplier="TestMake",
        price_usd=4000.0,
    ),
    "TestMake B-High Hashrate (250 TH/s)": MinerOption(
        name="TestMake B-High Hashrate",
        hashrate_th=250.0,
        power_w=4750,
        efficiency_j_per_th=19.0,
        supplier="TestMake",
        price_usd=5200.0,
    ),
    "TestMake C-Efficient Premium (200 TH/s)": MinerOption(
        name="TestMake C-Efficient Premium",
        hashrate_th=200.0,
        power_w=3200,
        efficiency_j_per_th=16.0,
        supplier="TestMake",
        price_usd=7000.0,
    ),
}

# Dev test hardware is not used for immediate deployment.
IMMEDIATE_ACCESS_MODELS: set[str] = set()
