# src/ui/scenario_1.py

from __future__ import annotations

import math
from typing import List, Optional

import altair as alt
import pandas as pd
import streamlit as st

from src.config import settings
from src.core.capex import CapexBreakdown
from src.core.scenario_engine import AnnualScenarioEconomics, ScenarioResult


def _format_currency(value: float) -> str:
    if value is None or math.isnan(value):
        return "£0"
    return f"£{value:,.0f}"


def _format_btc(value: float) -> str:
    if value is None or math.isnan(value):
        return "0 BTC"
    return f"{value:,.3f} BTC"


def _format_percentage(value: float) -> str:
    return f"{value * 100.0:,.1f}%"


def _format_years(value: float) -> str:
    if value is None or math.isnan(value) or math.isinf(value):
        return "No payback in project"
    if value < 0:
        return "N/A"
    return f"{value:,.1f} years"


def _build_years_dataframe(years: List[AnnualScenarioEconomics]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Year": y.year_index,
                "BTC mined": y.btc_mined,
                "Revenue (GBP)": y.revenue_gbp,
                "EBITDA (GBP)": y.ebitda_gbp,
                "Client net income (GBP)": y.client_net_income_gbp,
                "EBITDA margin (%)": y.ebitda_margin * 100.0,
            }
            for y in years
        ]
    )


def _render_headline_metrics(result: ScenarioResult) -> None:
    """
    Top 4–5 numbers you’d talk to a client about for this scenario.
    """

    total_capex = result.total_capex_gbp
    total_btc = result.total_btc
    total_net = result.total_client_net_income_gbp
    payback_years = result.client_payback_years
    roi_multiple = result.client_roi_multiple

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total BTC (project)",
            value=_format_btc(total_btc),
        )

    with col2:
        st.metric(
            label="Client net income (after tax)",
            value=_format_currency(total_net),
        )

    with col3:
        st.metric(
            label="Payback period (client)",
            value=_format_years(payback_years),
        )

    with col4:
        if total_capex > 0:
            st.metric(
                label="ROI multiple (net / CapEx)",
                value=f"{roi_multiple:,.2f}×",
            )
        else:
            st.metric(
                label="ROI multiple (net / CapEx)",
                value="N/A",
            )


def _render_revenue_split(result: ScenarioResult) -> None:
    """
    Simple row explaining who gets what from gross BTC revenue.
    """

    cfg = result.config
    client_share = cfg.client_revenue_share
    operator_share = 1.0 - client_share

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.caption("Client share of gross BTC revenue")
        st.write(_format_percentage(client_share))

    with col2:
        st.caption("21mScot share of gross BTC revenue")
        st.write(_format_percentage(operator_share))

    with col3:
        st.caption("Total revenue (project)")
        st.write(_format_currency(result.total_revenue_gbp))

    with col4:
        st.caption("Total client revenue vs operator revenue")
        st.write(
            f"{_format_currency(result.total_client_revenue_gbp)} "
            f"· {_format_currency(result.total_operator_revenue_gbp)}"
        )


def _render_yearly_chart(df: pd.DataFrame) -> None:
    """
    Combined view:
      - Bars: BTC mined per year (right-hand BTC axis)
      - Lines: Revenue & EBITDA per year (left-hand GBP axis)
    """

    if df.empty:
        st.info("No annual data available for this scenario.")
        return

    # -------------------------------------------------------------
    # BTC axis scaling: keep tallest bar at ~SCENARIO_BTC_BAR_MAX_FRACTION
    # of the BTC axis height (e.g. 0.6 = 60%).
    # -------------------------------------------------------------
    max_btc = float(df["BTC mined"].max()) if not df["BTC mined"].empty else 0.0
    if max_btc > 0 and 0.0 < settings.SCENARIO_BTC_BAR_MAX_FRACTION < 1.0:
        btc_axis_max = max_btc / settings.SCENARIO_BTC_BAR_MAX_FRACTION
        btc_scale = alt.Scale(domain=(0, btc_axis_max))
    else:
        btc_scale = alt.Scale(nice=True)

    # BTC bars on the RIGHT axis
    btc_bars = (
        alt.Chart(df)
        .mark_bar(
            opacity=settings.SCENARIO_BTC_BAR_OPACITY,
            color=settings.SCENARIO_BTC_BAR_COLOR,
        )
        .encode(
            x=alt.X(
                "Year:O",
                axis=alt.Axis(title="Year", labelAngle=0),  # labels horizontal
            ),
            y=alt.Y(
                "BTC mined:Q",
                title="BTC mined",
                axis=alt.Axis(title="BTC mined", orient="right"),
                scale=btc_scale,
            ),
        )
    )

    # Revenue & EBITDA lines on the LEFT axis (GBP)
    revenue_line = (
        alt.Chart(df)
        .mark_line(
            color=settings.SCENARIO_REVENUE_LINE_COLOR,
        )
        .encode(
            x="Year:O",
            y=alt.Y(
                "Revenue (GBP):Q",
                axis=alt.Axis(title="Revenue / EBITDA (GBP)", orient="left"),
            ),
        )
    )

    ebitda_line = (
        alt.Chart(df)
        .mark_line(
            color=settings.SCENARIO_EBITDA_LINE_COLOR,
            strokeDash=settings.SCENARIO_EBITDA_LINE_DASH,
        )
        .encode(
            x="Year:O",
            y=alt.Y(
                "EBITDA (GBP):Q",
                axis=None,  # share left GBP axis; avoid duplicate/jumbled axis
            ),
        )
    )

    # Independent y-scales so BTC and GBP ranges don't interfere
    chart = alt.layer(btc_bars, revenue_line, ebitda_line).resolve_scale(
        y="independent"
    )

    st.markdown("#### Annual gross revenue, EBITDA and BTC mined")
    st.altair_chart(chart, width="stretch")


def _render_yearly_table(df: pd.DataFrame) -> None:
    """
    Tabular annual breakdown for people who want to see the numbers.
    """

    if df.empty:
        return

    st.dataframe(
        df.style.format(
            {
                "BTC mined": "{:,.3f}",
                "Revenue (GBP)": "£{:,.0f}",
                "EBITDA (GBP)": "£{:,.0f}",
                "Client net income (GBP)": "£{:,.0f}",
                "EBITDA margin (%)": "{:,.1f}%",
            }
        ),
        width="stretch",
        hide_index=True,
    )


def _render_capex_breakdown(
    result: ScenarioResult,
    capex_breakdown: Optional[CapexBreakdown],
) -> None:
    """
    Show how the client's total CapEx is built up from assumptions.
    """

    if capex_breakdown is None or capex_breakdown.total_gbp == 0:
        st.info(
            "CapEx breakdown is not available. Define a site with supported ASICs "
            "on the Overview tab to see a model-based breakdown."
        )
        return

    model_total = capex_breakdown.total_gbp
    used_total = result.total_capex_gbp

    df = pd.DataFrame(
        [
            ("ASICs (miners)", capex_breakdown.asic_cost_gbp),
            ("Shipping", capex_breakdown.shipping_gbp),
            ("Import duty", capex_breakdown.import_duty_gbp),
            ("Spares allocation", capex_breakdown.spares_gbp),
            ("Racking / mounting", capex_breakdown.racking_gbp),
            ("Power & data cabling", capex_breakdown.cables_gbp),
            ("Switchgear & protection", capex_breakdown.switchgear_gbp),
            ("Networking & monitoring", capex_breakdown.networking_gbp),
            ("Installation labour", capex_breakdown.installation_labour_gbp),
            ("Certification & sign-off", capex_breakdown.certification_gbp),
        ],
        columns=["Component", "Cost (GBP)"],
    )

    st.dataframe(
        df.style.format({"Cost (GBP)": "£{:,.0f}"}),
        width="stretch",
        hide_index=True,
    )

    st.markdown(
        f"**Model-based CapEx total:** {_format_currency(model_total)}  \n"
        f"**CapEx used in this scenario:** {_format_currency(used_total)}"
    )

    if abs(model_total - used_total) > model_total * 0.05:
        st.caption(
            "Note: the scenario uses a different CapEx value than the model-based "
            "estimate (override applied in the control panel above)."
        )


def render_scenario_panel(
    result: ScenarioResult,
    capex_breakdown: Optional[CapexBreakdown] = None,
) -> None:
    """
    Main renderer used by the Scenarios & risks tab for a single scenario.
    """

    # Headline metrics (CapEx-aware, payback, ROI, net income, BTC)
    _render_headline_metrics(result)

    st.markdown("---")

    # Revenue split & totals
    _render_revenue_split(result)

    st.markdown("---")

    # Yearly chart + annual breakdown (expander)
    df = _build_years_dataframe(result.years)

    _render_yearly_chart(df)

    # 1) Annual breakdown expander CLOSED by default
    with st.expander("Annual breakdown", expanded=False):
        _render_yearly_table(df)

    #    st.markdown("---")

    # CapEx breakdown (client investment) as an optional drill-down
    with st.expander("CapEx breakdown (client investment)", expanded=False):
        _render_capex_breakdown(result, capex_breakdown)
