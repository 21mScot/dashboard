from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import streamlit as st


@dataclass
class MinerOption:
    """Represents a single ASIC miner option."""

    name: str
    hashrate_th: float  # terahash per second
    power_w: int  # watts
    efficiency_j_per_th: float  # joules per terahash
    supplier: str | None = None
    price_gbp: Optional[float] = None


# ---------------------------------------------------------------------------
# Static placeholder catalogue
# Later we replace this with API-loaded miners + filters.
# ---------------------------------------------------------------------------
_STATIC_MINER_OPTIONS: Dict[str, MinerOption] = {
    "Antminer S21 (200 TH/s)": MinerOption(
        name="Antminer S21 (200 TH/s)",
        hashrate_th=200.0,
        power_w=3500,
        efficiency_j_per_th=17.5,
        supplier="Bitmain",
        price_gbp=3100.0,
    ),
    "Whatsminer M60 (186 TH/s)": MinerOption(
        name="Whatsminer M60 (186 TH/s)",
        hashrate_th=186.0,
        power_w=3425,
        efficiency_j_per_th=18.4,
        supplier="MicroBT",
        price_gbp=2950.0,
    ),
    "Antminer S19k Pro (120 TH/s)": MinerOption(
        name="Antminer S19k Pro (120 TH/s)",
        hashrate_th=120.0,
        power_w=2760,
        efficiency_j_per_th=23.0,
        supplier="Bitmain",
        price_gbp=1800.0,
    ),
}


def load_miner_options() -> Iterable[MinerOption]:
    """
    Returns list of miners to display in the UI.

    Later replaced by:
      - API fetch
      - Filter by preferred suppliers
      - Filter by min efficiency, etc.
    """
    return _STATIC_MINER_OPTIONS.values()


def render_miner_selection() -> MinerOption:
    """Render the miner selection panel and return the chosen miner."""
    st.markdown("### 2. Miner selection")
    st.markdown(
        "Choose an ASIC model to explore site economics. "
        "We’ll use its hashrate, power draw and efficiency in later calculations."
    )

    miner_list = list(load_miner_options())
    options = [m.name for m in miner_list]

    selected_name = st.selectbox(
        "ASIC model",
        options,
        index=0,
        help="Select the ASIC model you are considering for this site.",
    )

    miner_lookup = {m.name: m for m in miner_list}
    miner = miner_lookup[selected_name]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Hashrate", f"{miner.hashrate_th:.0f} TH/s")
        st.metric("Power draw", f"{miner.power_w} W")

    with col2:
        st.metric("Efficiency", f"{miner.efficiency_j_per_th:.1f} J/TH")
        if miner.price_gbp:
            st.metric("Indicative price", f"£{miner.price_gbp:,.0f}")
        else:
            st.metric("Indicative price", "—")

    if miner.supplier:
        st.caption(f"Supplier: {miner.supplier}")

    st.caption(
        "Specs are indicative and can be refined from vendor data or live APIs "
        "in a later iteration."
    )

    return miner
