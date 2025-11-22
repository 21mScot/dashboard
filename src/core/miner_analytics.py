# src/core/miner_analytics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics
from src.core.miner_models import MinerOption


@dataclass
class BreakevenPoint:
    miner: str
    efficiency_j_per_th: float
    breakeven_price_gbp_per_kwh: Optional[float]


@dataclass
class PaybackPoint:
    miner: str
    efficiency_j_per_th: float
    power_price_gbp_per_kwh: float
    payback_days: Optional[float]


def _uptime_factor(uptime_pct: float) -> float:
    return max(0.0, min(uptime_pct, 100.0)) / 100.0


def compute_breakeven_points(
    miners: Iterable[MinerOption],
    network: NetworkData,
    uptime_pct: float,
) -> List[BreakevenPoint]:
    """Return breakeven price per miner in £/kWh."""
    uptime = _uptime_factor(uptime_pct)
    points: List[BreakevenPoint] = []

    for miner in miners:
        econ = compute_miner_economics(miner.hashrate_th, network)
        revenue_gbp = econ.revenue_usd_per_day * network.usd_to_gbp * uptime
        kwh_day = (miner.power_w / 1000.0) * 24.0 * uptime
        breakeven_price = revenue_gbp / kwh_day if kwh_day > 0 else None
        points.append(
            BreakevenPoint(
                miner=miner.name,
                efficiency_j_per_th=miner.efficiency_j_per_th,
                breakeven_price_gbp_per_kwh=breakeven_price,
            )
        )
    return points


def compute_payback_points(
    miners: Iterable[MinerOption],
    network: NetworkData,
    uptime_pct: float,
    power_prices_gbp: Iterable[float],
    breakeven_map: Optional[dict[str, Optional[float]]] = None,
    cap_days: Optional[float] = None,
) -> List[PaybackPoint]:
    """
    Compute payback curves. If breakeven_map is provided, points beyond breakeven
    are excluded. If cap_days is set, points above the cap are excluded for
    chart readability.
    """
    uptime = _uptime_factor(uptime_pct)
    points: List[PaybackPoint] = []

    for miner in miners:
        econ = compute_miner_economics(miner.hashrate_th, network)
        revenue_gbp = econ.revenue_usd_per_day * network.usd_to_gbp * uptime
        kwh_day = (miner.power_w / 1000.0) * 24.0 * uptime
        price_gbp = (miner.price_usd or 0.0) * network.usd_to_gbp
        miner_breakeven = breakeven_map.get(miner.name) if breakeven_map else None

        for power_price in power_prices_gbp:
            if miner_breakeven is not None and power_price > miner_breakeven:
                continue

            profit = revenue_gbp - kwh_day * power_price
            if profit <= 0 or price_gbp <= 0:
                payback = None
            else:
                payback = price_gbp / profit

            if cap_days is not None and payback is not None and payback > cap_days:
                continue

            points.append(
                PaybackPoint(
                    miner=miner.name,
                    efficiency_j_per_th=miner.efficiency_j_per_th,
                    power_price_gbp_per_kwh=power_price,
                    payback_days=payback,
                )
            )

    return points


def build_viability_summary(
    miners: Iterable[MinerOption],
    breakeven_map: dict[str, Optional[float]],
    site_price_gbp_per_kwh: float,
    payback_points: List[PaybackPoint],
) -> List[dict[str, Optional[float | str]]]:
    """Summarize viability and payback at the site price for each miner."""
    summary: List[dict[str, Optional[float | str]]] = []

    # Pre-index payback points at site price for quick lookup
    payback_at_price: dict[str, Optional[float]] = {}
    for point in payback_points:
        if abs(point.power_price_gbp_per_kwh - site_price_gbp_per_kwh) < 1e-9:
            payback_at_price[point.miner] = point.payback_days

    for miner in miners:
        breakeven_price = breakeven_map.get(miner.name)
        viable = (
            breakeven_price is not None
            and site_price_gbp_per_kwh is not None
            and breakeven_price >= site_price_gbp_per_kwh
        )
        summary.append(
            {
                "Miner": miner.name,
                "Viable at site": "Yes" if viable else "No",
                "Breakeven price (p/kWh)": (
                    breakeven_price * 100 if breakeven_price is not None else None
                ),
                "Payback at site price (days)": payback_at_price.get(miner.name),
            }
        )

    return summary
