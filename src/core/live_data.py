# src/core/live_data.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import requests

from src.config.settings import (
    BLOCK_SUBSIDY_BTC,
    BLOCKCHAIN_DIFFICULTY_URL,
    COINGECKO_SIMPLE_PRICE_URL,
    LIVE_DATA_REQUEST_TIMEOUT_S,
    LIVE_DATA_USER_AGENT,
    MEMPOOL_BLOCKTIP_URL,
)


@dataclass(slots=True)
class NetworkData:
    btc_price_usd: float
    difficulty: float
    block_subsidy_btc: float
    block_height: Optional[int] = None


class LiveDataError(RuntimeError):
    """Raised when live data cannot be fetched."""


# ---------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------


def _http_get(url: str, **kwargs) -> requests.Response:
    """
    Thin wrapper around requests.get so we have a single place
    to set headers, timeouts, etc.
    """
    headers = kwargs.pop("headers", {}) or {}
    headers.setdefault("User-Agent", LIVE_DATA_USER_AGENT)

    return requests.get(
        url,
        headers=headers,
        timeout=LIVE_DATA_REQUEST_TIMEOUT_S,
        **kwargs,
    )


# ---------------------------------------------------------
# BTC Price
# ---------------------------------------------------------


def _get_btc_price_usd() -> float:
    resp = _http_get(
        COINGECKO_SIMPLE_PRICE_URL,
        params={"ids": "bitcoin", "vs_currencies": "usd"},
    )
    resp.raise_for_status()
    data = resp.json()

    try:
        price = float(data["bitcoin"]["usd"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LiveDataError(f"Unexpected price payload from CoinGecko: {data}") from exc

    return price


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
    diff_resp = _http_get(BLOCKCHAIN_DIFFICULTY_URL)
    diff_resp.raise_for_status()

    # blockchain.info/q/getdifficulty returns the difficulty as plain text float
    try:
        difficulty = float(diff_resp.text.strip())
    except ValueError as exc:
        raise LiveDataError(
            f"Unexpected difficulty payload from blockchain.info: {diff_resp.text!r}"
        ) from exc

    # --- block height (optional best-effort) ---
    height: int | None
    try:
        height_resp = _http_get(MEMPOOL_BLOCKTIP_URL)
        height_resp.raise_for_status()
        # mempool.space /api/v1/blocks/tip-height returns a bare JSON integer
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

    Block subsidy is currently BLOCK_SUBSIDY_BTC (post-2024 halving); we
    hard-code it in settings instead of hitting another API.
    """
    try:
        price = _get_btc_price_usd()
        difficulty, height = _get_difficulty_and_height()
    except LiveDataError:
        # Pass through our own errors unchanged
        raise
    except Exception as exc:  # pragma: no cover - safety net
        raise LiveDataError(f"Failed to fetch live data: {exc}") from exc

    return NetworkData(
        btc_price_usd=price,
        difficulty=difficulty,
        block_subsidy_btc=BLOCK_SUBSIDY_BTC,
        block_height=height,
    )
