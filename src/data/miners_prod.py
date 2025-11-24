# src/data/miners_prod.py
from __future__ import annotations

from typing import Dict

from src.core.miner_models import MinerOption

# Previous production catalogue retained for manual comparison.
PREVIOUS_MINERS: Dict[str, MinerOption] = {
    "Antminer S21 (200 TH/s)": MinerOption(
        name="Antminer S21",
        hashrate_th=200.0,
        power_w=3500,
        efficiency_j_per_th=17.5,
        supplier="Bitmain",
        price_usd=3100.0,
    ),
    "Whatsminer M60 (186 TH/s)": MinerOption(
        name="Whatsminer M60",
        hashrate_th=186.0,
        power_w=3425,
        efficiency_j_per_th=18.4,
        supplier="MicroBT",
        price_usd=2950.0,
    ),
    "Antminer S19k Pro (120 TH/s)": MinerOption(
        name="Antminer S19k Pro",
        hashrate_th=120.0,
        power_w=2760,
        efficiency_j_per_th=23.0,
        supplier="Bitmain",
        price_usd=1800.0,
    ),
    "Whatsminer M63S++ (480 TH/s)": MinerOption(
        name="Whatsminer M63S++",
        hashrate_th=480.0,
        power_w=7200,
        efficiency_j_per_th=15.5,
        supplier="MicroBT",
        price_usd=6600.0,
    ),
    "Whatsminer M33S (240 TH/s)": MinerOption(
        name="Whatsminer M33S",
        hashrate_th=240.0,
        power_w=7260,
        efficiency_j_per_th=30.0,
        supplier="MicroBT",
        price_usd=600.0,
    ),
}

# Production catalogue: synced with co-founder spreadsheet.
MINERS: Dict[str, MinerOption] = {
    "M33 H++ (242 TH/s)": MinerOption(
        name="M33 H++",
        hashrate_th=242.0,
        power_w=7260,
        efficiency_j_per_th=30.0,
        supplier="MicroBT",
        price_usd=600.0,
    ),
    "M63 H (478 TH/s)": MinerOption(
        name="M63 H",
        hashrate_th=478.0,
        power_w=7399,
        efficiency_j_per_th=15.48,
        supplier="MicroBT",
        price_usd=7409.0,
    ),
    "S19 H+ (279 TH/s)": MinerOption(
        name="S19 H+",
        hashrate_th=279.0,
        power_w=5300,
        efficiency_j_per_th=19.0,
        supplier="Bitmain",
        price_usd=2511.0,
    ),
    "S21 XP+ Hydro (500 TH/s)": MinerOption(
        name="S21 XP+ Hydro",
        hashrate_th=500.0,
        power_w=5500,
        efficiency_j_per_th=11.0,
        supplier="Bitmain",
        price_usd=7834.0,
    ),
    "S23 H+ (580 TH/s)": MinerOption(
        name="S23 H+",
        hashrate_th=580.0,
        power_w=5500,
        efficiency_j_per_th=9.48,
        supplier="Bitmain",
        price_usd=14500.0,
    ),
}

# Highlight models where rapid delivery is available (none flagged in new list).
IMMEDIATE_ACCESS_MODELS: set[str] = set()
