# src/core/live_data.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    as_of_utc: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    hashprice_usd_per_ph_day: Optional[float] = None
    hashprice_as_of_utc: Optional[datetime] = None


class LiveDataError(RuntimeError):
    """Raised when live data cannot be fetched."""


def _fetch_btc_price_usd() -> tuple[float, datetime]:
    """Fetch BTC price in USD from CoinGecko, with Coinbase as a quick fallback."""
    fetched_at = datetime.now(timezone.utc)
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
        return float(data["bitcoin"]["usd"]), fetched_at
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
            return float(cb_data["data"]["amount"]), datetime.now(timezone.utc)
        except (KeyError, TypeError, ValueError) as exc:
            raise LiveDataError(
                f"Unexpected price payload from Coinbase: {cb_data}"
            ) from exc


def _fetch_difficulty_and_height() -> tuple[float, Optional[int], datetime]:
    """
    Fetch Bitcoin difficulty and (optionally) block height.
    Difficulty: blockchain.info
    Height: mempool.space
    """
    fetched_at = datetime.now(timezone.utc)
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

    return difficulty, height, fetched_at


def _fetch_usd_to_gbp_rate() -> tuple[float, datetime]:
    """
    Fetch USD/GBP FX rate with a resilient fallback chain.

    Primary: Frankfurter (ECB-backed, FOSS)
    Secondary: exchangerate.host (public, free)
    Final fallback: static default so other live data can still be used.
    """
    fetched_at = datetime.now(timezone.utc)
    try:
        resp = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "GBP"},
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        api_date = data.get("date")
        as_of = (
            datetime.strptime(api_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if api_date
            else fetched_at
        )
        return float(data["rates"]["GBP"]), as_of
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
            api_date = data.get("date")
            as_of = (
                datetime.strptime(api_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if api_date
                else datetime.now(timezone.utc)
            )
            return float(data["rates"]["GBP"]), as_of
        except Exception:
            # Do not block BTC/difficulty if FX is temporarily down
            return float(settings.DEFAULT_USD_TO_GBP), datetime.now(timezone.utc)


def _fetch_hashprice_usd_per_ph_day() -> tuple[Optional[float], Optional[datetime]]:
    """
    Fetch Luxor Hashprice (USD per PH/s per day).

    This is informational only; failures should not block the dashboard.
    """
    try:
        resp = requests.get(
            settings.HASHRATEINDEX_HASHPRICE_URL,
            headers={"User-Agent": settings.LIVE_DATA_USER_AGENT},
            timeout=settings.LIVE_DATA_REQUEST_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        usd = data.get("usd")
        ts_raw = data.get("timestamp") or data.get("time") or data.get("updatedAt")

        ts: Optional[datetime] = None
        if isinstance(ts_raw, (int, float)):
            ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        elif isinstance(ts_raw, str):
            # Try ISO string with/without Z
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except Exception:
                ts = None

        return (float(usd) if usd is not None else None), ts
    except Exception:
        return None, None


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
        price, price_ts = _fetch_btc_price_usd()
        difficulty, height, diff_ts = _fetch_difficulty_and_height()
        usd_to_gbp, fx_ts = _fetch_usd_to_gbp_rate()
        hashprice_usd_per_ph_day, hashprice_ts = _fetch_hashprice_usd_per_ph_day()
    except Exception as exc:
        raise LiveDataError(f"Failed to fetch live data: {exc}") from exc

    timestamps = [ts for ts in (price_ts, diff_ts, fx_ts, hashprice_ts) if ts]
    as_of_utc = max(timestamps) if timestamps else datetime.now(timezone.utc)

    return NetworkData(
        btc_price_usd=price,
        difficulty=difficulty,
        block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
        usd_to_gbp=usd_to_gbp,
        block_height=height,
        as_of_utc=as_of_utc,
        hashprice_usd_per_ph_day=hashprice_usd_per_ph_day,
        hashprice_as_of_utc=hashprice_ts,
    )
