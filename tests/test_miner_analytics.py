# tests/test_miner_analytics.py

from src.config import settings
from src.core.live_data import NetworkData
from src.core.miner_analytics import (
    build_viability_summary,
    compute_breakeven_points,
    compute_payback_points,
)
from src.core.miner_models import MinerOption


def _sample_network() -> NetworkData:
    return NetworkData(
        btc_price_usd=settings.DEFAULT_BTC_PRICE_USD,
        difficulty=settings.DEFAULT_NETWORK_DIFFICULTY,
        block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
        usd_to_gbp=settings.DEFAULT_USD_TO_GBP,
        block_height=None,
    )


def _sample_miner() -> MinerOption:
    return MinerOption(
        name="TestMiner",
        hashrate_th=100.0,
        power_w=3000,
        efficiency_j_per_th=30.0,
        supplier=None,
        price_usd=1500.0,
    )


def test_compute_breakeven_points_returns_price():
    miner = _sample_miner()
    network = _sample_network()

    points = compute_breakeven_points([miner], network, uptime_pct=100.0)
    assert len(points) == 1
    assert points[0].breakeven_price_gbp_per_kwh is not None
    assert points[0].breakeven_price_gbp_per_kwh > 0


def test_payback_points_clip_at_breakeven_and_cap():
    miner = _sample_miner()
    network = _sample_network()
    breakeven = compute_breakeven_points([miner], network, uptime_pct=100.0)[0]
    breakeven_price = breakeven.breakeven_price_gbp_per_kwh or 0.1

    prices = [
        max(0.001, breakeven_price - 0.01),
        breakeven_price + 0.01,  # should be clipped out
    ]
    cap_days = 1000

    payback_points = compute_payback_points(
        miners=[miner],
        network=network,
        uptime_pct=100.0,
        power_prices_gbp=prices,
        breakeven_map={miner.name: breakeven_price},
        cap_days=cap_days,
    )

    # Only prices at/below breakeven are kept, and payback is capped
    assert all(p.power_price_gbp_per_kwh <= breakeven_price for p in payback_points)
    assert all(
        (p.payback_days or 0) <= cap_days for p in payback_points if p.payback_days
    )


def test_viability_summary_reports_site_payback():
    miner = _sample_miner()
    network = _sample_network()
    breakeven = compute_breakeven_points([miner], network, uptime_pct=100.0)[0]
    breakeven_price = breakeven.breakeven_price_gbp_per_kwh or 0.05
    site_price = breakeven_price - 0.005

    payback_points = compute_payback_points(
        miners=[miner],
        network=network,
        uptime_pct=100.0,
        power_prices_gbp=[site_price],
        breakeven_map={miner.name: breakeven_price},
        cap_days=None,
    )

    summary = build_viability_summary(
        miners=[miner],
        breakeven_map={miner.name: breakeven_price},
        site_price_gbp_per_kwh=site_price,
        payback_points=payback_points,
    )
    assert summary[0]["Viable at site"] == "Yes"
    assert summary[0]["Payback at site price (days)"] is not None
