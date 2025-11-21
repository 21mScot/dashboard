# src/ui/miner_selection.py

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, Optional

import streamlit as st

from src.core.live_data import NetworkData
from src.core.miner_economics import compute_miner_economics
from src.core.miner_models import MinerOption

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
        price_usd=6600.0,
    ),
    "Whatsminer M33S (240 TH/s)": MinerOption(
        name="Whatsminer M33S",
        hashrate_th=240.0,
        power_w=7260,
        efficiency_j_per_th=30.0,
        supplier="MicroBT",
        price_usd=600.0,
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
# Non-UI helpers
# ---------------------------------------------------------------------------
def _load_sorted_miners() -> list[MinerOption]:
    """Miners sorted by hashrate descending."""
    return list(_get_hashrate_sorted_miners().values())


def get_current_selected_miner() -> Optional[MinerOption]:
    """Return the miner stored in session_state (if any)."""
    options = _load_sorted_miners()
    by_name = {m.name: m for m in options}
    current_name = st.session_state.get("selected_miner_name")
    if not current_name:
        return None
    return by_name.get(current_name)


def clear_selected_miner() -> None:
    """Clear any persisted miner selection."""
    st.session_state.pop("selected_miner_name", None)
    st.session_state.pop("selected_miner_label", None)


def _estimate_payback_days(
    miner: MinerOption,
    network: NetworkData,
    power_price_gbp_per_kwh: float,
    uptime_pct: float,
) -> Optional[float]:
    """Estimate simple payback in days; returns None if not viable."""
    uptime_factor = max(0.0, min(uptime_pct, 100.0)) / 100.0

    econ = compute_miner_economics(miner.hashrate_th, network)
    revenue_usd_per_day = econ.revenue_usd_per_day * uptime_factor
    revenue_gbp_per_day = revenue_usd_per_day * network.usd_to_gbp

    kwh_per_day = (miner.power_w / 1000.0) * 24.0 * uptime_factor
    power_cost_gbp_per_day = kwh_per_day * power_price_gbp_per_kwh

    profit_gbp_per_day = revenue_gbp_per_day - power_cost_gbp_per_day
    if profit_gbp_per_day <= 0:
        return None

    price_gbp = (miner.price_usd or 0.0) * network.usd_to_gbp
    if price_gbp <= 0:
        return None

    return price_gbp / profit_gbp_per_day


def maybe_autoselect_miner(
    site_power_kw: float,
    power_price_gbp_per_kwh: float,
    uptime_pct: float,
    network: NetworkData,
) -> None:
    """
    If the user has started entering inputs and no miner is selected yet,
    choose the miner with the lowest simple payback (if viable).
    """
    if st.session_state.get("selected_miner_name"):
        return

    # Trigger only after any of the key inputs have been touched.
    if all(
        val in (None, 0, 0.0)
        for val in (site_power_kw, power_price_gbp_per_kwh, uptime_pct)
    ):
        return

    options = _load_sorted_miners()
    if not options:
        return

    best_miner: Optional[MinerOption] = None
    best_payback: Optional[float] = None

    for miner in options:
        payback = _estimate_payback_days(
            miner=miner,
            network=network,
            power_price_gbp_per_kwh=power_price_gbp_per_kwh,
            uptime_pct=uptime_pct,
        )
        if payback is None:
            continue
        if best_payback is None or payback < best_payback:
            best_payback = payback
            best_miner = miner

    if best_miner:
        st.session_state["selected_miner_name"] = best_miner.name


def render_miner_picker(
    label: str = "Alternative ASIC miners",
) -> Optional[MinerOption]:
    """Render a selectbox for miners and return the chosen MinerOption (or None)."""
    options = sorted(
        _load_sorted_miners(), key=lambda m: m.efficiency_j_per_th
    )  # best (lower J/TH) first
    by_label = {
        (
            f"{m.name} — {m.efficiency_j_per_th:.1f} J/TH · "
            f"{m.hashrate_th:.0f} TH/s · {m.power_w} W"
        ): m
        for m in options
    }
    placeholder = "Select a miner"
    labels = [placeholder] + list(by_label.keys())

    current_miner = get_current_selected_miner()
    if current_miner:
        current_label = next(
            (
                lbl
                for lbl, miner in by_label.items()
                if miner.name == current_miner.name
            ),
            placeholder,
        )
    else:
        current_label = placeholder

    selected_label = st.selectbox(
        label,
        options=labels,
        index=labels.index(current_label),
        help="Select from currently available miners.",
        key="selected_miner_label",
    )

    if selected_label == placeholder:
        return current_miner

    selected_miner = by_label[selected_label]
    if not current_miner or selected_miner.name != current_miner.name:
        st.session_state["selected_miner_name"] = selected_miner.name
        rerun_fn = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
        if rerun_fn:
            rerun_fn()

    return selected_miner


# ---------------------------------------------------------------------------
