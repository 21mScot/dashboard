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
    """Fetch BTC price in USD from CoinGecko, with Coinbase as a quick fallback."""
    # Primary: CoinGecko
    try:
        resp = requests.get(
            settings.COINGECKO_SIMPLE_PRICE_URL,
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["bitcoin"]["usd"])
    except Exception:
        # Secondary: Coinbase spot price (no API key required)
        cb_resp = requests.get(
            "https://api.coinbase.com/v2/prices/spot",
            params={"currency": "USD"},
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        cb_resp.raise_for_status()
        cb_data = cb_resp.json()
        try:
            return float(cb_data["data"]["amount"])
        except (KeyError, TypeError, ValueError) as exc:
            raise LiveDataError(
                f"Unexpected price payload from Coinbase: {cb_data}"
            ) from exc


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
    Fetch USD/GBP FX rate with a resilient fallback chain.

    Primary: Frankfurter (ECB-backed, FOSS)
    Secondary: exchangerate.host (public, free)
    Final fallback: static default so other live data can still be used.
    """
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "GBP"},
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["rates"]["GBP"])
    except Exception:
        # Secondary provider
        try:
            resp = requests.get(
                "https://api.exchangerate.host/latest",
                params={"base": "USD", "symbols": "GBP"},
                headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
                timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
            )
            resp.raise_for_status()
            data = resp.json()
            return float(data["rates"]["GBP"])
        except Exception:
            # Do not block BTC/difficulty if FX is temporarily down
            return float(settings.DEFAULT_USD_TO_GBP)


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
