# tests/test_prod_miner_outputs.py
from datetime import datetime, timezone

import pytest

from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics
from src.data import miners_prod


def _static_network() -> NetworkData:
    return NetworkData(
        btc_price_usd=90_000.0,
        difficulty=150_000_000_000_000,
        block_subsidy_btc=3.125,
        usd_to_gbp=0.75,
        block_height=None,
        as_of_utc=datetime(2025, 1, 1, tzinfo=timezone.utc),
        hashprice_usd_per_ph_day=None,
        hashprice_as_of_utc=None,
    )


@pytest.mark.parametrize(
    "miner_key, expected_btc, expected_revenue_usd, power_price",
    [
        ("M63 H (478 TH/s)", 0.0002003275, 18.02947, 0.059),
        ("S23 H+ (580 TH/s)", 0.0002430752, 21.87677, 0.059),
    ],
)
def test_prod_miner_outputs_with_power_cost(
    miner_key: str,
    expected_btc: float,
    expected_revenue_usd: float,
    power_price: float,
):
    network = _static_network()
    miner = miners_prod.MINERS[miner_key]
    econ = compute_miner_economics(miner.hashrate_th, network)

    # Revenue and BTC/day from the core engine
    assert econ.btc_per_day == pytest.approx(expected_btc, rel=1e-4)
    assert econ.revenue_usd_per_day == pytest.approx(expected_revenue_usd, rel=1e-3)

    # Power cost and net with a non-zero $/kWh input
    kwh_per_day = (miner.power_w / 1000.0) * 24.0
    power_cost_usd = kwh_per_day * power_price
    net_usd = econ.revenue_usd_per_day - power_cost_usd

    expected_power_cost = kwh_per_day * power_price
    assert power_cost_usd == pytest.approx(expected_power_cost, rel=1e-6)

    expected_net = expected_revenue_usd - expected_power_cost
    assert net_usd == pytest.approx(expected_net, rel=1e-3)
