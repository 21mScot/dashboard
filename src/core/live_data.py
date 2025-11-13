# src/core/live_data.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"
MEMPOOL_BLOCKTIP_URL = "https://mempool.space/api/v1/blocks/tip-height"

# Simple difficulty endpoint that returns a raw number
BLOCKCHAIN_DIFFICULTY_URL = "https://blockchain.info/q/getdifficulty"


@dataclass
class NetworkData:
    btc_price_usd: float
    difficulty: float
    block_subsidy_btc: float
    block_height: Optional[int] = None


class LiveDataError(RuntimeError):
    """Raised when live data cannot be fetched."""


# ---------------------------------------------------------
# BTC Price
# ---------------------------------------------------------


def _get_btc_price_usd() -> float:
    resp = requests.get(
        COINGECKO_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return float(data["bitcoin"]["usd"])


# ---------------------------------------------------------
# Difficulty + Height
# ---------------------------------------------------------


def _get_difficulty_and_height() -> tuple[float, int | None]:
    """
    Fetch the current Bitcoin network difficulty and (optionally)
    the latest block height.
    Difficulty comes from blockchain.info,
    height from mempool.space.
    """

    # --- difficulty ---
    diff_resp = requests.get(BLOCKCHAIN_DIFFICULTY_URL, timeout=10)
    diff_resp.raise_for_status()
    # blockchain.info/q/getdifficulty returns the difficulty as plain text float
    difficulty = float(diff_resp.text.strip())

    # --- block height (optional) ---
    try:
        height_resp = requests.get(MEMPOOL_BLOCKTIP_URL, timeout=10)
        height_resp.raise_for_status()
        height = int(height_resp.json())
    except Exception:
        height = None

    return difficulty, height


# ---------------------------------------------------------
# Public-facing API
# ---------------------------------------------------------


def get_live_network_data() -> NetworkData:
    """
    Fetch current BTC price + network difficulty from public APIs.

    Block subsidy is currently 3.125 BTC (post-2024 halving); we hard-code it
    instead of hitting another API.
    """
    try:
        price = _get_btc_price_usd()
        difficulty, height = _get_difficulty_and_height()
    except Exception as exc:
        raise LiveDataError(f"Failed to fetch live data: {exc}") from exc

    return NetworkData(
        btc_price_usd=price,
        difficulty=difficulty,
        block_subsidy_btc=3.125,
        block_height=height,
    )
