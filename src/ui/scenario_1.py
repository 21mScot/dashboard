# src/ui/scenario_1.py

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from src.core.scenarios_period import (
    ScenarioAnnualEconomics,
    annual_economics_to_dataframe,
)


def _build_scenario_1_figure(econ: ScenarioAnnualEconomics):
    """
    Create a dual-axis chart for Scenario 1:

    - X-axis: Year
    - Left Y-axis (fiat, £): Revenue, OpEx, Profit (EBITDA)
    - Right Y-axis (BTC): BTC mined per year (bars)
    """
    years = [row.year_index for row in econ.years]

    btc_mined = [row.btc_mined for row in econ.years]
    revenue = [row.revenue_fiat for row in econ.years]
    opex = [row.total_opex_fiat for row in econ.years]
    profit = [row.ebitda_fiat for row in econ.years]  # EBITDA as operating profit

    fig, ax1 = plt.subplots()

    # --- Left axis: fiat (£) ---
    ax1.set_xlabel("Year")
    ax1.set_ylabel("£ (fiat)")

    (line_revenue,) = ax1.plot(
        years,
        revenue,
        marker="o",
        label="Revenue (£)",
        color="blue",
    )
    (line_opex,) = ax1.plot(
        years,
        opex,
        marker="o",
        label="OpEx (£)",
        color="red",
    )
    (line_profit,) = ax1.plot(
        years,
        profit,
        marker="o",
        label="Profit (£)",
        color="green",
    )

    ax1.grid(True, axis="y", linestyle="--", alpha=0.3)

    # --- Right axis: BTC ---
    ax2 = ax1.twinx()
    ax2.set_ylabel("BTC mined")

    bars_btc = ax2.bar(
        years,
        btc_mined,
        alpha=0.3,
        label="BTC mined",
        color="grey",
    )

    # --- Legend (combine both axes) ---
    handles = [line_revenue, line_opex, line_profit, bars_btc]
    labels = [h.get_label() for h in handles]
    ax1.legend(handles, labels, loc="upper left")

    fig.tight_layout()
    return fig


def render_scenario_1(econ: ScenarioAnnualEconomics) -> None:
    """
    Render the Scenario 1 MVP: annual economics only.
    Assumes `econ` has already been computed (or is dummy data).
    """
    st.subheader("Scenario 1 – Annual site economics")

    st.caption(
        "Annual site-level economics based on Scenario 1 assumptions. "
        "This view excludes CapEx, revenue share, and tax effects for clarity."
    )

    # --- Top summary metrics ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total BTC (all years)",
            value=f"{econ.total_btc:,.3f}",
        )

    with col2:
        st.metric(
            label="Total revenue (£)",
            value=f"£{econ.total_revenue:,.0f}",
        )

    with col3:
        st.metric(
            label="Total OpEx (£)",
            value=f"£{econ.total_opex:,.0f}",
        )

    with col4:
        st.metric(
            label="Avg EBITDA margin",
            value=f"{econ.avg_ebitda_margin * 100:,.1f}%",
        )

    st.markdown("---")

    # --- Chart ---
    st.markdown("#### Annual economics chart")

    fig = _build_scenario_1_figure(econ)
    st.pyplot(fig)

    st.markdown("---")

    # --- Annual table in an expander ---
    with st.expander("Show annual economics table", expanded=False):
        st.markdown("#### Annual economics table")

        df = annual_economics_to_dataframe(econ)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )
