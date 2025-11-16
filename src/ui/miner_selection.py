# src/ui/miner_selection.py

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import streamlit as st

from src.core.live_data import NetworkData


@dataclass
class MinerOption:
    """Represents a single ASIC miner option.

    All pricing here is in USD. Site-level economics are responsible
    for converting USD -> GBP (or other local currencies).
    """

    name: str
    hashrate_th: float  # terahash per second
    power_w: int  # watts
    efficiency_j_per_th: float  # joules per terahash
    supplier: str | None = None
    price_usd: Optional[float] = None


# ---------------------------------------------------------------------------
# Static placeholder catalogue
# Later we replace this with API-loaded miners + filters.
# Prices are indicative USD values for POC purposes.
# ---------------------------------------------------------------------------
_STATIC_MINER_OPTIONS: Dict[str, MinerOption] = {
    "Antminer S21 (200 TH/s)": MinerOption(
        name="Antminer S21 (200 TH/s)",
        hashrate_th=200.0,
        power_w=3500,
        efficiency_j_per_th=17.5,
        supplier="Bitmain",
        price_usd=3100.0,
    ),
    "Whatsminer M60 (186 TH/s)": MinerOption(
        name="Whatsminer M60 (186 TH/s)",
        hashrate_th=186.0,
        power_w=3425,
        efficiency_j_per_th=18.4,
        supplier="MicroBT",
        price_usd=2950.0,
    ),
    "Antminer S19k Pro (120 TH/s)": MinerOption(
        name="Antminer S19k Pro (120 TH/s)",
        hashrate_th=120.0,
        power_w=2760,
        efficiency_j_per_th=23.0,
        supplier="Bitmain",
        price_usd=1800.0,
    ),
    "Whatsminer M63S++ (480 TH/s)": MinerOption(
        name="Whatsminer M63S++ (480 TH/s)",
        hashrate_th=480.0,
        power_w=7200,
        efficiency_j_per_th=15.5,
        supplier="MicroBT",
        price_usd=6600.0,
    ),
    "Whatsminer M33S (240 TH/s)": MinerOption(
        name="Whatsminer M33S (240 TH/s)",
        hashrate_th=240.0,
        power_w=7260,
        efficiency_j_per_th=30.0,
        supplier="MicroBT",
        price_usd=660.0,
    ),
}
# ---------------------------------------------------------------------------

# Models available for immediate deployment
_IMMEDIATE_ACCESS_MODELS: set[str] = {
    "Whatsminer M63S++ (480 TH/s)",
    "Whatsminer M33S (240 TH/s)",
}


# ---------------------------------------------------------------------------
# Sorting helpers
# ---------------------------------------------------------------------------
def _get_efficiency_sorted_miners() -> OrderedDict[str, MinerOption]:
    """
    Return miners sorted by efficiency (J/TH), ascending.
    Lower J/TH = better efficiency.
    """
    sorted_pairs = sorted(
        _STATIC_MINER_OPTIONS.items(),
        key=lambda item: item[1].efficiency_j_per_th,
    )
    return OrderedDict(sorted_pairs)


def load_miner_options() -> Iterable[MinerOption]:
    """
    Returns list of miners to display in the UI.

    Later replaced by:
      - API fetch
      - Filter by preferred suppliers
      - Filter by min efficiency, etc.
    """
    return _STATIC_MINER_OPTIONS.values()


# ---------- helpers for live economics ----------
def _estimate_btc_per_day(miner: MinerOption, network: NetworkData) -> float:
    """
    Very simple expected BTC/day estimate from:
      - miner hashrate
      - network difficulty
      - current block subsidy
    """
    miner_hashrate_hs = miner.hashrate_th * 1e12
    network_hashrate_hs = network.difficulty * (2**32) / 600.0

    share_of_network = miner_hashrate_hs / network_hashrate_hs
    btc_per_day = share_of_network * network.block_subsidy_btc * 144
    return btc_per_day


def _estimate_network_hashrate_ths(network: NetworkData) -> float:
    network_hashrate_hs = network.difficulty * (2**32) / 600.0
    return network_hashrate_hs / 1e12


# ---------------------------------------------------------------------------
# UI rendering
# ---------------------------------------------------------------------------
def render_miner_selection(
    network_data: NetworkData | None = None,
) -> MinerOption:
    """
    Render the miner selection UI and return the chosen MinerOption.
    If `network_data` is provided, show live BTC/day and revenue comparisons.
    """
    st.markdown("### 2. Miner selection")
    st.markdown(
        "Choose an ASIC model to explore site economics. "
        "We’ll use its hashrate, power draw and efficiency in later calculations."
    )

    # Use miners sorted by efficiency
    sorted_miners = _get_efficiency_sorted_miners()
    options = list(sorted_miners.keys())

    selected_name = st.selectbox(
        "ASIC model (sorted by efficiency — lowest J/TH first)",
        options,
        index=0,
        help="Select the ASIC model you are considering for this site.",
    )

    miner = sorted_miners[selected_name]

    # Immediate access highlight
    if selected_name in _IMMEDIATE_ACCESS_MODELS:
        st.success(
            "⚡ **Immediate Access Available**\n\n"
            "This model is available for rapid deployment from our priority stock.\n"
            "- Lead time: *Immediate–2 weeks*\n"
            "- Great for proof-of-concepts or urgent scaling"
        )

    # Display specs
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Hashrate", f"{miner.hashrate_th:.0f} TH/s")
        st.metric("Power draw", f"{miner.power_w} W")

    with col2:
        st.metric("Efficiency", f"{miner.efficiency_j_per_th:.1f} J/TH")
        if miner.price_usd:
            st.metric("Indicative price (USD)", f"${miner.price_usd:,.0f}")
        else:
            st.metric("Indicative price (USD)", "—")

    if miner.supplier:
        st.caption(f"Supplier: {miner.supplier}")

    st.caption(
        "Specs and prices are indicative only. They can be refined from vendor "
        "quotes or live APIs in a later iteration."
    )

    # Live network calculations
    if network_data is not None:
        st.markdown("#### Live network estimate for this miner")

        btc_per_day = _estimate_btc_per_day(miner, network_data)
        revenue_usd = btc_per_day * network_data.btc_price_usd

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("BTC / day (live)", f"{btc_per_day:.5f} BTC")
        with col_b:
            st.metric("Revenue / day (USD, live)", f"${revenue_usd:,.2f}")

        network_hashrate_ths = _estimate_network_hashrate_ths(network_data)
        st.metric(
            "Estimated network hashrate",
            f"{network_hashrate_ths:,.0f} TH/s",
            help="Derived from current Bitcoin difficulty.",
        )
    else:
        st.info(
            "Live BTC/day and revenue estimates are temporarily unavailable. "
            "We’re using static assumptions elsewhere in the app."
        )

    return miner
