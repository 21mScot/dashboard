# src/core/live_data.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests
import streamlit as st

from src.config import settings

# ---------------------------------------------------------
# Data Model
# ---------------------------------------------------------


@dataclass
class NetworkData:
    btc_price_usd: float
    difficulty: float
    block_subsidy_btc: float
    block_height: Optional[int] = None


class LiveDataError(RuntimeError):
    """Raised when live data cannot be fetched."""


# ---------------------------------------------------------
# Internal fetch helpers (no caching here)
# ---------------------------------------------------------


def _fetch_btc_price_usd() -> float:
    """Fetch BTC price in USD from Coingecko."""
    resp = requests.get(
        settings.COINGECKO_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return float(data["bitcoin"]["usd"])


def _fetch_difficulty_and_height() -> tuple[float, Optional[int]]:
    """
    Fetch Bitcoin difficulty and (optionally) block height.
    Difficulty: blockchain.info
    Height: mempool.space
    """

    # Difficulty
    diff_resp = requests.get(settings.BLOCKCHAIN_DIFFICULTY_URL, timeout=10)
    diff_resp.raise_for_status()
    difficulty = float(diff_resp.text.strip())

    # Block height (optional)
    try:
        height_resp = requests.get(settings.MEMPOOL_BLOCKTIP_URL, timeout=10)
        height_resp.raise_for_status()
        height = int(height_resp.json())
    except Exception:
        height = None

    return difficulty, height


# ---------------------------------------------------------
# Cached public API entry point
# ---------------------------------------------------------


@st.cache_data(ttl=settings.LIVE_DATA_TTL_HOURS * 3600, show_spinner=False)
def _fetch_network_data_cached() -> NetworkData:
    """Cached wrapper around all external API calls."""
    print("🔌 Hitting external APIs for live BTC network data")  # DEBUG
    try:
        price = _fetch_btc_price_usd()
        difficulty, height = _fetch_difficulty_and_height()

        return NetworkData(
            btc_price_usd=price,
            difficulty=difficulty,
            block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
            block_height=height,
        )

    except Exception as exc:
        # Raise a structured error so UI can present a fallback panel
        raise LiveDataError(f"Failed to fetch live data: {exc}") from exc


def get_live_network_data() -> NetworkData:
    """
    Public-facing function for the rest of the app.
    Always returns one of:

    - Cached live network data
    - OR raises LiveDataError (UI must handle with fallbacks)

    This ensures:
    - No duplicated API hits
    - No re-fetching on UI interactions
    - Safe consistent behaviour across the app
    """
    return _fetch_network_data_cached()
