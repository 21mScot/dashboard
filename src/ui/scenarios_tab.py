# src/ui/scenarios_tab.py
from __future__ import annotations

from typing import Optional

import streamlit as st

from src.core.scenario_engine import ScenarioResult
from src.ui.scenario_1 import render_scenario_panel


def _build_scenario_label(
    result: ScenarioResult,
    friendly_name: str,
) -> str:
    """
    Build a one-line label for the expander based on a ScenarioResult.

    Example:
      'Scenario 1 – Base case · 4 years · 1.23 BTC · £123,456 revenue'
    """

    n_years = len(result.years)
    total_btc = result.total_btc
    total_revenue = result.total_revenue_gbp

    return (
        f"{friendly_name} · "
        f"{n_years} year{'s' if n_years != 1 else ''} · "
        f"{total_btc:,.3f} BTC · "
        f"£{total_revenue:,.0f} revenue"
    )


def render_scenarios_tab(
    base_result: ScenarioResult,
    best_result: Optional[ScenarioResult] = None,
    worst_result: Optional[ScenarioResult] = None,
) -> None:
    """
    Layout container for the Scenarios tab.

    Expects fully computed ScenarioResult objects from the engine layer
    and arranges them into expanders. Each expander reuses the same
    renderer (render_scenario_panel) so all scenarios share a consistent
    visual structure.
    """

    st.subheader("Scenario 1 – Project economics")

    # Base case – expanded by default
    with st.expander(
        _build_scenario_label(base_result, "Scenario 1 – Base case"),
        expanded=True,
    ):
        render_scenario_panel(base_result)

    # Best case
    if best_result is not None:
        with st.expander(
            _build_scenario_label(best_result, "Scenario 1 – Best case"),
            expanded=False,
        ):
            render_scenario_panel(best_result)

    # Worst case
    if worst_result is not None:
        with st.expander(
            _build_scenario_label(worst_result, "Scenario 1 – Worst case"),
            expanded=False,
        ):
            render_scenario_panel(worst_result)
