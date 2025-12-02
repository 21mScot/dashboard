# src/data/miners_dev.py
from __future__ import annotations

from typing import Dict, Tuple

from src.core.miner_models import MinerOption

# Legacy set used for WhatToMine validation
LEGACY_WTM_MINERS: Dict[str, MinerOption] = {
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
}

# ChatGPT test trio (spread for efficiency/breakeven/payback testing)
CHATGPT_TEST_MINERS: Dict[str, MinerOption] = {
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

IMMEDIATE_ACCESS_MODELS: set[str] = set()
CHATGPT_TEST_IMMEDIATE: set[str] = set()


def get_dev_catalogue(
    key: str,
) -> Tuple[Dict[str, MinerOption], set[str]]:
    """Return the requested dev miner catalogue and any immediate-access set."""
    normalized = (key or "").strip().lower()
    if normalized == "prod":
        # Allow dev environments to surface the full production catalogue.
        from src.data import miners_prod

        return miners_prod.MINERS, getattr(
            miners_prod, "IMMEDIATE_ACCESS_MODELS", set()
        )
    if normalized == "chatgpt_test":
        return CHATGPT_TEST_MINERS, CHATGPT_TEST_IMMEDIATE
    # default to legacy validation set
    return LEGACY_WTM_MINERS, IMMEDIATE_ACCESS_MODELS


# Backwards compatibility: default MINERS points to the legacy validation set.
MINERS = LEGACY_WTM_MINERS
