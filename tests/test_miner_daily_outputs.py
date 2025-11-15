# tests/test_miner_daily_outputs.py
import pytest

from src.config import settings
from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics

# --- truth-engine functions -------------------------------------------------


def btc_per_day(hashrate_th: float, network: NetworkData) -> float:
    """
    Expected BTC/day for a miner with `hashrate_th` (TH/s),
    given network difficulty and block subsidy in `network`.
    Assumes 100% uptime and no pool fees.
    """
    hashrate_hs = hashrate_th * 1e12  # TH/s -> H/s
    difficulty = float(network.difficulty)
    block_subsidy = float(network.block_subsidy_btc)

    blocks_per_day = 144
    network_hashrate_hs = difficulty * 2**32 / 600  # H/s

    share = hashrate_hs / network_hashrate_hs
    return share * block_subsidy * blocks_per_day


def revenue_per_day(
    hashrate_th: float,
    network: NetworkData,
    usd_per_btc: float | None = None,
    usd_to_gbp: float = 0.8,  # tweak to your FX assumption
):
    """
    Returns (btc_day, usd_day, gbp_day) for a given miner.
    """
    if usd_per_btc is None:
        usd_per_btc = float(network.btc_price_usd)

    btc_day = btc_per_day(hashrate_th, network)
    usd_day = btc_day * usd_per_btc
    gbp_day = usd_day * usd_to_gbp
    return btc_day, usd_day, gbp_day


# --- fixtures / shared network setup ----------------------------------------


@pytest.fixture(scope="module")
def static_network() -> NetworkData:
    return NetworkData(
        btc_price_usd=settings.DEFAULT_BTC_PRICE_USD,
        difficulty=settings.DEFAULT_NETWORK_DIFFICULTY,
        block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
        block_height=None,
    )


def test_s21_daily_outputs(static_network: NetworkData):
    econ = compute_miner_economics(200, static_network)
    assert econ.btc_per_day == pytest.approx(0.0000838190, rel=1e-4)
    assert econ.revenue_usd_per_day == pytest.approx(7.54, rel=1e-2)


def test_m60_daily_outputs(static_network: NetworkData):
    econ = compute_miner_economics(186, static_network)
    assert econ.btc_per_day == pytest.approx(0.0000779517, rel=1e-4)
    assert econ.revenue_usd_per_day == pytest.approx(7.02, rel=1e-2)


def test_s19kpro_daily_outputs(static_network: NetworkData):
    econ = compute_miner_economics(120, static_network)
    assert econ.btc_per_day == pytest.approx(0.0000502914, rel=1e-4)
    assert econ.revenue_usd_per_day == pytest.approx(4.53, rel=1e-2)


# --- optional: keep the script-style output for manual inspection -----------


def main():
    network = NetworkData(
        btc_price_usd=settings.DEFAULT_BTC_PRICE_USD,
        difficulty=settings.DEFAULT_NETWORK_DIFFICULTY,
        block_subsidy_btc=settings.DEFAULT_BLOCK_SUBSIDY_BTC,
        block_height=None,
    )

    miners = {
        "Antminer S21 (200 TH/s)": 200,
        "Whatsminer M60 (186 TH/s)": 186,
        "Antminer S19k Pro (120 TH/s)": 120,
    }

    print("Using network data:")
    print(f"  BTC price (USD): {network.btc_price_usd:,.0f}")
    print(f"  Difficulty:      {network.difficulty:,.0f}")
    print(f"  Block subsidy:   {network.block_subsidy_btc} BTC\n")

    for name, h_th in miners.items():
        btc_day, usd_day, gbp_day = revenue_per_day(h_th, network)
        print(f"{name}")
        print(f"  Hashrate:   {h_th} TH/s")
        print(f"  BTC / day:  {btc_day:.8f}")
        print(f"  USD / day:  ${usd_day:,.2f}")
        print(f"  GBP / day:  £{gbp_day:,.2f}")
        print()


if __name__ == "__main__":
    main()
