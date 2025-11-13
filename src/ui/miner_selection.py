from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

import pandas as pd
import streamlit as st

from src.core.live_data import NetworkData


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


# ---------- helpers for live economics ----------


def _estimate_btc_per_day(miner: MinerOption, network: NetworkData) -> float:
    """
    Very simple expected BTC/day estimate from:
      - miner hashrate
      - network difficulty
      - current block subsidy
    """
    # Miner hashrate in H/s
    miner_hashrate_hs = miner.hashrate_th * 1e12

    # Network hashrate in H/s
    # difficulty * 2^32 / 600 ≈ hashes per second
    network_hashrate_hs = network.difficulty * (2**32) / 600.0

    share_of_network = miner_hashrate_hs / network_hashrate_hs
    blocks_per_day = 144  # ~10 min block time
    btc_per_day = share_of_network * network.block_subsidy_btc * blocks_per_day
    return btc_per_day


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

    # ---------- live BTC / revenue estimate for the selected miner ----------
    if network_data is not None:
        st.markdown("#### Live network estimate for this miner")

        btc_per_day = _estimate_btc_per_day(miner, network_data)
        revenue_usd_per_day = btc_per_day * network_data.btc_price_usd

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("BTC / day (live)", f"{btc_per_day:.5f} BTC")
        with col_b:
            st.metric(
                "Revenue / day (USD, live)",
                f"${revenue_usd_per_day:,.2f}",
            )

        # ---------- variance between all miners ----------
        rows = []
        for m in miner_list:
            m_btc = _estimate_btc_per_day(m, network_data)
            m_rev = m_btc * network_data.btc_price_usd
            rows.append(
                {
                    "Model": m.name,
                    "Hashrate (TH/s)": m.hashrate_th,
                    "Power (W)": m.power_w,
                    "Eff. (J/TH)": m.efficiency_j_per_th,
                    "BTC / day": m_btc,
                    "Revenue / day (USD)": m_rev,
                    "Indicative price (GBP)": m.price_gbp,
                }
            )

        df = pd.DataFrame(rows).set_index("Model")

        st.markdown("#### Variance between miners (live data)")
        st.dataframe(
            df.style.format(
                {
                    "Hashrate (TH/s)": "{:.0f}",
                    "Power (W)": "{:.0f}",
                    "Eff. (J/TH)": "{:.1f}",
                    "BTC / day": "{:.5f}",
                    "Revenue / day (USD)": "${:,.2f}",
                    "Indicative price (GBP)": "£{:,.0f}",
                }
            )
        )
    else:
        st.info(
            "Toggle **'Use live BTC network data'** in the sidebar to see BTC/day and "
            "revenue comparisons between miners."
        )

    return miner
