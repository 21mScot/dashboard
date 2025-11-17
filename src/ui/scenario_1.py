# src/ui/scenario_1.py
from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from src.config import settings
from src.core.scenario_engine import (
    AnnualScenarioEconomics,
    ScenarioResult,
)


# ---------------------------------------------------------
# Convert scenario years → DataFrame
# ---------------------------------------------------------
def _scenario_years_to_dataframe(
    years: list[AnnualScenarioEconomics],
) -> pd.DataFrame:
    """
    Convert the per-year scenario economics into a tabular form suitable
    for display and download.

    Ordering principle:
      - Fiat-denominated metrics first
      - Margin (%)
      - BTC metrics last
    """

    records = []
    for y in years:
        records.append(
            {
                "Year": y.year_index,
                # Fiat first
                "Gross revenue (£)": y.revenue_gbp,
                "Electricity cost (£)": y.electricity_cost_gbp,
                "Other opex (£)": y.other_opex_gbp,
                "Total opex (£)": y.total_opex_gbp,
                "EBITDA (£)": y.ebitda_gbp,
                "EBITDA margin (%)": y.ebitda_margin * 100.0,
                "Client share of revenue (£)": y.client_revenue_gbp,
                "21mScot share of revenue (£)": y.operator_revenue_gbp,
                "Client tax (£)": y.client_tax_gbp,
                "Net income (£)": y.client_net_income_gbp,
                # BTC last
                "BTC mined": y.btc_mined,
                "BTC price (USD)": y.btc_price_usd,
            }
        )

    df = pd.DataFrame.from_records(records)
    return df.set_index("Year")


# ---------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------
def _render_headline_metrics(result: ScenarioResult) -> None:
    """
    Headline metrics used during client conversation.

    Ordering:
      1. Net income (£)
      2. Gross revenue (£)
      3. Total OpEx (£)
      4. Avg EBITDA margin (%)
      5. Total BTC (project)
    """

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        st.metric(
            label="Net income (£)",
            value=f"£{result.total_client_net_income_gbp:,.0f}",
        )

    with c2:
        st.metric(
            label="Gross revenue (£)",
            value=f"£{result.total_revenue_gbp:,.0f}",
        )

    with c3:
        st.metric(
            label="Total OpEx (£)",
            value=f"£{result.total_opex_gbp:,.0f}",
        )

    with c4:
        st.metric(
            label="Avg EBITDA margin (%)",
            value=f"{result.avg_ebitda_margin * 100:,.1f}",
        )

    with c5:
        st.metric(
            label="Total BTC (project)",
            value=f"{result.total_btc:,.3f}",
        )


# ---------------------------------------------------------
# Annual chart: revenue, EBITDA, BTC mined
# ---------------------------------------------------------
def _render_revenue_chart(df: pd.DataFrame) -> None:
    """
    Chart of annual gross revenue and EBITDA (left axis, £)
    plus BTC mined (right axis, BTC) as a bar/histogram.

    - Revenue & EBITDA share the *same* left-hand £ axis and scale.
    - BTC mined has its own right-hand axis, with domain scaled so the
      tallest bar reaches approximately SCENARIO_BTC_BAR_MAX_FRACTION
      of the BTC axis height.

    Visual styling is controlled by constants in settings.py.
    """

    chart_df = df.reset_index().rename(columns={"Year": "Year"})

    base = alt.Chart(chart_df).encode(x=alt.X("Year:O", title="Year"))

    # ---------- BTC axis scaling (right-hand axis) ----------

    max_btc = float(chart_df["BTC mined"].max() or 0.0)
    target_frac = getattr(settings, "SCENARIO_BTC_BAR_MAX_FRACTION", 0.6)

    if max_btc > 0 and 0 < target_frac < 1:
        btc_domain_max = max_btc / target_frac
    else:
        btc_domain_max = max_btc or 1.0

    btc_axis = alt.Axis(
        title="BTC mined",
        orient="right",
        tickCount=4,
        format=".2f",
    )

    btc_bars = base.mark_bar(
        opacity=getattr(settings, "SCENARIO_BTC_BAR_OPACITY", 0.25),
        color=getattr(settings, "SCENARIO_BTC_BAR_COLOR", "#E9ECF1"),
        strokeWidth=getattr(settings, "SCENARIO_BTC_BAR_STROKE_WIDTH", 0),
    ).encode(
        y=alt.Y(
            "BTC mined:Q",
            axis=btc_axis,
            scale=alt.Scale(domain=[0, btc_domain_max]),
        ),
        tooltip=[
            "Year:O",
            alt.Tooltip("BTC mined:Q", format=".3f", title="BTC mined"),
        ],
    )

    # ---------- Fiat lines (left-hand axis, shared) ----------

    # Left axis definition (shared by revenue + EBITDA)
    left_axis_y = alt.Y(
        "Gross revenue (£):Q",
        axis=alt.Axis(title="£ (fiat)", orient="left"),
    )

    revenue_line = base.mark_line(
        point=True,
        color=getattr(settings, "SCENARIO_REVENUE_LINE_COLOR", "#1f77b4"),
    ).encode(
        y=left_axis_y,
        tooltip=[
            "Year:O",
            alt.Tooltip("Gross revenue (£):Q", format=",.0f"),
            alt.Tooltip("EBITDA (£):Q", format=",.0f"),
            alt.Tooltip("BTC mined:Q", format=".3f"),
        ],
    )

    # EBITDA shares the same left scale; we suppress its own axis
    ebitda_line = base.mark_line(
        point=True,
        color=getattr(settings, "SCENARIO_EBITDA_LINE_COLOR", "#2ca02c"),
        strokeDash=getattr(settings, "SCENARIO_EBITDA_LINE_DASH", [4, 2]),
    ).encode(
        y=alt.Y("EBITDA (£):Q", axis=None),
    )

    # Make sure fiat lines share the same y-scale
    fiat_layer = alt.layer(revenue_line, ebitda_line).resolve_scale(y="shared")

    # Put BTC bars *behind* the fiat lines (Option A)
    chart = (
        alt.layer(btc_bars, fiat_layer)
        .resolve_scale(y="independent")  # left (fiat) vs right (BTC)
        .properties(height=300)
    )

    st.altair_chart(chart, width="stretch")


# ---------------------------------------------------------
# Render full scenario panel
# ---------------------------------------------------------
def render_scenario_panel(result: ScenarioResult) -> None:
    """
    Render one scenario: headline metrics, chart, and detailed table.

    Parent layout (scenarios_tab.py) decides how many scenarios exist
    and how they are labelled.
    """

    df = _scenario_years_to_dataframe(result.years)

    _render_headline_metrics(result)

    st.markdown("### Annual gross revenue, EBITDA and BTC mined")
    _render_revenue_chart(df)

    st.markdown("### Detailed annual economics")

    with st.expander("Show annual economics table", expanded=False):
        st.dataframe(df.style.format(precision=2))

        csv = df.to_csv().encode("utf-8")
        st.download_button(
            label="Download annual economics as CSV",
            data=csv,
            file_name=f"scenario_{result.config.name}_annual_economics.csv",
            mime="text/csv",
        )
