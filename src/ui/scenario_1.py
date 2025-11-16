# src/ui/scenario_1.py
from __future__ import annotations

import pandas as pd
import streamlit as st

from src.core.scenario_engine import (
    AnnualScenarioEconomics,
    ScenarioResult,
)


def _scenario_years_to_dataframe(
    years: list[AnnualScenarioEconomics],
) -> pd.DataFrame:
    """
    Convert the per-year scenario economics into a tabular form suitable
    for display and download. This is where we define the client-facing
    columns and their ordering.
    """

    records = []
    for y in years:
        records.append(
            {
                "Year": y.year_index,
                "BTC mined": y.btc_mined,
                "BTC price (USD)": y.btc_price_usd,
                "Revenue (£)": y.revenue_gbp,
                "Electricity cost (£)": y.electricity_cost_gbp,
                "Other opex (£)": y.other_opex_gbp,
                "Total opex (£)": y.total_opex_gbp,
                "EBITDA (£)": y.ebitda_gbp,
                "EBITDA margin (%)": y.ebitda_margin * 100.0,
                "Client revenue (£)": y.client_revenue_gbp,
                "21mScot revenue (£)": y.operator_revenue_gbp,
                "Client tax (£)": y.client_tax_gbp,
                "Client net income (£)": y.client_net_income_gbp,
            }
        )

    df = pd.DataFrame.from_records(records)
    return df.set_index("Year")


def _render_headline_metrics(result: ScenarioResult) -> None:
    """
    Show a small set of headline metrics for quick orientation during
    client conversations.
    """

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="Total BTC (project)",
            value=f"{result.total_btc:,.3f}",
        )

    with c2:
        st.metric(
            label="Total revenue (£)",
            value=f"£{result.total_revenue_gbp:,.0f}",
        )

    with c3:
        st.metric(
            label="Total client net income (£)",
            value=f"£{result.total_client_net_income_gbp:,.0f}",
        )

    with c4:
        st.metric(
            label="Avg EBITDA margin (%)",
            value=f"{result.avg_ebitda_margin * 100:,.1f}",
        )


def _render_revenue_chart(df: pd.DataFrame) -> None:
    """
    Simple chart of annual revenue and EBITDA to visually anchor the
    conversation. You can refine or replace this later.
    """

    chart_data = df[["Revenue (£)", "EBITDA (£)"]]
    st.line_chart(chart_data)


def render_scenario_panel(result: ScenarioResult) -> None:
    """
    Render one scenario: headline metrics, chart, and detailed table
    inside a nested expander.

    This function does not know anything about 'base/best/worst' – it
    just renders the ScenarioResult it's given. The parent layout
    (scenarios_tab.py) decides how many scenarios there are and how
    they are labelled.
    """

    df = _scenario_years_to_dataframe(result.years)

    _render_headline_metrics(result)

    st.markdown("### Annual revenue and EBITDA")
    _render_revenue_chart(df)

    st.markdown("### Detailed annual economics")

    with st.expander("Show annual economics table", expanded=False):
        st.dataframe(df.style.format(precision=2))

        csv = df.to_csv().encode("utf-8")
        st.download_button(
            label="Download table as CSV",
            data=csv,
            file_name=f"scenario_{result.config.name}_annual_economics.csv",
            mime="text/csv",
        )
