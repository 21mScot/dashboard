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
# Static placeholder catalogue (prices & specs indicative only)
# ---------------------------------------------------------------------------
_STATIC_MINER_OPTIONS: Dict[str, MinerOption] = {
    "Antminer S21 (200 TH/s)": MinerOption(
        name="Antminer S21",
        hashrate_th=200.0,
        power_w=3500,
        efficiency_j_per_th=17.5,
        supplier="Bitmain",
        price_usd=3100.0,
    ),
    "Whatsminer M60 (186 TH/s)": MinerOption(
        name="Whatsminer M60",
        hashrate_th=186.0,
        power_w=3425,
        efficiency_j_per_th=18.4,
        supplier="MicroBT",
        price_usd=2950.0,
    ),
    "Antminer S19k Pro (120 TH/s)": MinerOption(
        name="Antminer S19k Pro",
        hashrate_th=120.0,
        power_w=2760,
        efficiency_j_per_th=23.0,
        supplier="Bitmain",
        price_usd=1800.0,
    ),
    "Whatsminer M63S++ (480 TH/s)": MinerOption(
        name="Whatsminer M63S++",
        hashrate_th=480.0,
        power_w=7200,
        efficiency_j_per_th=15.5,
        supplier="MicroBT",
        price_usd=5000.0,
    ),
    "Whatsminer M33S (240 TH/s)": MinerOption(
        name="Whatsminer M33S",
        hashrate_th=240.0,
        power_w=7260,
        efficiency_j_per_th=30.0,
        supplier="MicroBT",
        price_usd=500.0,
    ),
}


# Models available for immediate deployment (use dict keys)
_IMMEDIATE_ACCESS_MODELS: set[str] = {
    "Whatsminer M63S++ (480 TH/s)",
    "Whatsminer M33S (240 TH/s)",
}


# ---------------------------------------------------------------------------
# Sorting helpers
# ---------------------------------------------------------------------------
def _get_hashrate_sorted_miners() -> OrderedDict[str, MinerOption]:
    """Return miners sorted by hashrate (TH/s), descending.

    Highest TH/s first → highest BTC/day first (for a given network snapshot).
    """
    sorted_pairs = sorted(
        _STATIC_MINER_OPTIONS.items(),
        key=lambda item: item[1].hashrate_th,
        reverse=True,
    )
    return OrderedDict(sorted_pairs)


def load_miner_options() -> Iterable[MinerOption]:
    """Return list of miners to display in the UI."""
    return _STATIC_MINER_OPTIONS.values()


# ---------------------------------------------------------------------------
# Economics helpers
# ---------------------------------------------------------------------------
def _estimate_btc_per_day(miner: MinerOption, network: NetworkData) -> float:
    """Expected BTC/day for a given miner under a network snapshot."""
    miner_hashrate_hs = miner.hashrate_th * 1e12
    network_hashrate_hs = network.difficulty * (2**32) / 600.0
    share = miner_hashrate_hs / network_hashrate_hs
    return share * network.block_subsidy_btc * 144


def _estimate_network_hashrate_ths(network: NetworkData) -> float:
    """Estimated global hashrate (TH/s) from difficulty."""
    return (network.difficulty * (2**32) / 600.0) / 1e12


# ---------------------------------------------------------------------------
# UI: Miner selection
# ---------------------------------------------------------------------------
def render_miner_selection(
    network_data: NetworkData | None = None,
) -> MinerOption:
    """Render miner selection UI and return selected MinerOption."""

    st.markdown("### 2. Choose your miner model")
    st.markdown(
        "Choose an ASIC model to explore site economics. "
        "We’ll use its hashrate, power draw and efficiency in later calculations."
    )

    # Sort miners by hashrate (TH/s), highest first → highest BTC/day first
    sorted_miners = _get_hashrate_sorted_miners()

    # Build labels: name → TH/s → power
    option_labels: list[str] = []
    label_to_key: dict[str, str] = {}

    for key, m in sorted_miners.items():
        label = f"{m.name} — {m.hashrate_th:.0f} TH/s, {m.power_w} W"
        option_labels.append(label)
        label_to_key[label] = key

    selected_label = st.selectbox(
        "ASIC model (sorted by hashrate, highest TH/s first)",
        option_labels,
        index=0,
        help=(
            "Models are ordered by hashrate (TH/s), highest first. "
            "Higher TH/s means more BTC/day for a given network snapshot. "
            "Labels show: name, hashrate (TH/s) and power draw (W)."
        ),
    )

    selected_key = label_to_key[selected_label]
    miner = sorted_miners[selected_key]

    # Immediate access highlight
    if selected_key in _IMMEDIATE_ACCESS_MODELS:
        st.success(
            "⚡ **Immediate Access Available**\n\n"
            "This model is available for rapid deployment from our priority stock.\n"
            "- Lead time: *Immediate–2 weeks*\n"
            "- Suitable for PoCs or rapid scaling"
        )

    # Specs
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Hashrate", f"{miner.hashrate_th:.0f} TH/s")
        st.metric("Power draw", f"{miner.power_w} W")
    with col2:
        st.metric("Efficiency", f"{miner.efficiency_j_per_th:.1f} J/TH")
        st.metric(
            "Indicative price (USD)",
            f"${miner.price_usd:,.0f}" if miner.price_usd else "—",
        )

    if miner.supplier:
        st.caption(f"Supplier: {miner.supplier}")

    st.caption("Specs and pricing are indicative only and may vary by supplier.")

    # Live calculations
    if network_data is not None:
        st.markdown("#### Live network estimate for this miner")

        btc_per_day = _estimate_btc_per_day(miner, network_data)
        revenue_usd = btc_per_day * network_data.btc_price_usd

        colA, colB = st.columns(2)
        with colA:
            st.metric("BTC / day", f"{btc_per_day:.5f} BTC")
        with colB:
            st.metric("Revenue / day (USD)", f"${revenue_usd:,.2f}")

        st.metric(
            "Estimated network hashrate",
            f"{_estimate_network_hashrate_ths(network_data):,.0f} TH/s",
        )
    else:
        st.info(
            "Live BTC/day and revenue unavailable "
            "— static assumptions are used elsewhere."
        )

    return miner


# ---------------------------------------------------------------------------
