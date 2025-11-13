# src/ui/scenarios_tab.py

from __future__ import annotations

import streamlit as st

from src.core.scenarios_period import (
    AnnualEconomicsRow,
    ScenarioAnnualEconomics,
)
from src.ui.scenario_1 import render_scenario_1


def _build_dummy_scenario_1() -> ScenarioAnnualEconomics:
    """Temporary placeholder data for Scenario 1."""
    year1_btc = 6.5
    year1_price = 50_000.0
    year1_rev = year1_btc * year1_price
    year1_elec = 22_000.0
    year1_other = 0.0
    year1_opex = year1_elec + year1_other
    year1_ebitda = year1_rev - year1_opex
    year1_margin = year1_ebitda / year1_rev

    year2_btc = 6.0
    year2_price = 55_000.0
    year2_rev = year2_btc * year2_price
    year2_elec = 23_000.0
    year2_other = 0.0
    year2_opex = year2_elec + year2_other
    year2_ebitda = year2_rev - year2_opex
    year2_margin = year2_ebitda / year2_rev

    year3_btc = 5.5
    year3_price = 60_000.0
    year3_rev = year3_btc * year3_price
    year3_elec = 24_000.0
    year3_other = 0.0
    year3_opex = year3_elec + year3_other
    year3_ebitda = year3_rev - year3_opex
    year3_margin = year3_ebitda / year3_rev

    year4_btc = 5.0
    year4_price = 65_000.0
    year4_rev = year4_btc * year4_price
    year4_elec = 25_000.0
    year4_other = 0.0
    year4_opex = year4_elec + year4_other
    year4_ebitda = year4_rev - year4_opex
    year4_margin = year4_ebitda / year4_rev

    return ScenarioAnnualEconomics(
        name="Scenario 1 – Base case",
        years=[
            AnnualEconomicsRow(
                year_index=1,
                btc_mined=year1_btc,
                btc_price_fiat=year1_price,
                revenue_fiat=year1_rev,
                electricity_cost_fiat=year1_elec,
                other_opex_fiat=year1_other,
                total_opex_fiat=year1_opex,
                ebitda_fiat=year1_ebitda,
                ebitda_margin=year1_margin,
            ),
            AnnualEconomicsRow(
                year_index=2,
                btc_mined=year2_btc,
                btc_price_fiat=year2_price,
                revenue_fiat=year2_rev,
                electricity_cost_fiat=year2_elec,
                other_opex_fiat=year2_other,
                total_opex_fiat=year2_opex,
                ebitda_fiat=year2_ebitda,
                ebitda_margin=year2_margin,
            ),
            AnnualEconomicsRow(
                year_index=3,
                btc_mined=year3_btc,
                btc_price_fiat=year3_price,
                revenue_fiat=year3_rev,
                electricity_cost_fiat=year3_elec,
                other_opex_fiat=year3_other,
                total_opex_fiat=year3_opex,
                ebitda_fiat=year3_ebitda,
                ebitda_margin=year3_margin,
            ),
            AnnualEconomicsRow(
                year_index=4,
                btc_mined=year4_btc,
                btc_price_fiat=year4_price,
                revenue_fiat=year4_rev,
                electricity_cost_fiat=year4_elec,
                other_opex_fiat=year4_other,
                total_opex_fiat=year4_opex,
                ebitda_fiat=year4_ebitda,
                ebitda_margin=year4_margin,
            ),
        ],
    )


def render_scenarios_tab() -> None:
    """Render Scenario 1 annual economics inside the Scenarios tab."""
    scenario1 = _build_dummy_scenario_1()

    with st.expander("Scenario 1 – Base case", expanded=True):
        render_scenario_1(scenario1)
