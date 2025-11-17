# src/core/live_data.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from src.config import settings

# ---------------------------------------------------------
# Data model
# ---------------------------------------------------------


@dataclass(slots=True)
class NetworkData:
    btc_price_usd: float
    difficulty: float
    block_subsidy_btc: float
    usd_to_gbp: float
    block_height: Optional[int] = None


class LiveDataError(RuntimeError):
    """Raised when live data cannot be fetched."""


# ---------------------------------------------------------
# Internal fetch helpers (no caching here)
# ---------------------------------------------------------


def _fetch_btc_price_usd() -> float:
    """Fetch BTC price in USD from CoinGecko."""
    resp = requests.get(
        settings.COINGECKO_SIMPLE_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
        headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
        timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    data = resp.json()

    try:
        price = float(data["bitcoin"]["usd"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LiveDataError(f"Unexpected price payload from CoinGecko: {data}") from exc

    return price


def _fetch_difficulty_and_height() -> tuple[float, Optional[int]]:
    """
    Fetch Bitcoin difficulty and (optionally) block height.
    Difficulty: blockchain.info
    Height: mempool.space
    """
    # Difficulty
    diff_resp = requests.get(
        settings.BLOCKCHAIN_DIFFICULTY_URL,
        headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
        timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
    )
    diff_resp.raise_for_status()
    difficulty = float(diff_resp.text.strip())

    # Block height (optional)
    try:
        height_resp = requests.get(
            settings.MEMPOOL_BLOCKTIP_URL,
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        height_resp.raise_for_status()
        # mempool.space /api/v1/blocks/tip-height returns a bare JSON integer
        height = int(height_resp.json())
    except Exception:
        height = None

    return difficulty, height


def _fetch_usd_to_gbp_rate() -> float:
    """
    Fetch USD/GBP FX rate from a FOSS source (Frankfurter API).

    Frankfurter is a free, open-source API backed by ECB rates:
    https://www.frankfurter.app/
    """
    resp = requests.get(
        "https://api.frankfurter.app/latest",
        params={"from": "USD", "to": "GBP"},
        headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
        timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
    )
    resp.raise_for_status()
    data = resp.json()

    try:
        # Example payload:
        # {"amount":1.0,"base":"USD","date":"2025-01-01","rates":{"GBP":0.79}}
        rate = float(data["rates"]["GBP"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LiveDataError(f"Unexpected FX payload from Frankfurter: {data}") from exc

    return rate


# ---------------------------------------------------------
# Public API
# ---------------------------------------------------------


def get_live_network_data() -> NetworkData:
    """
    Public-facing function for the rest of the app.

    UI (layout.py) is responsible for:
    - caching via st.cache_data
    - handling LiveDataError and falling back to static defaults
    """
    try:
        price = _fetch_btc_price_usd()
        difficulty, height = _fetch_difficulty_and_height()
        usd_to_gbp = _fetch_usd_to_gbp_rate()
    except Exception as exc:
        raise LiveDataError(f"Failed to fetch live data: {exc}") from exc

    return NetworkData(
        btc_price_usd=price,
        difficulty=difficulty,
        block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
        usd_to_gbp=usd_to_gbp,
        block_height=height,
    )
