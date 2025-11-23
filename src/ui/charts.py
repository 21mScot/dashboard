# src/ui/charts.py
from __future__ import annotations

from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import settings


def render_btc_forecast_chart(
    df: pd.DataFrame,
    title: str = "BTC forecast (monthly)",
    show_cumulative: bool = True,
) -> None:
    """
    Render the core BTC economics forecast chart.

    Expected df columns:
    - month: datetime64[ns] (monthly)
    - btc_mined_month: float (BTC mined in that month)

    Optional:
    - btc_cumulative: float (cumulative BTC; if missing, will be computed)
    - is_halving: bool (True where a halving occurs in that month)
    - halving_label: str (label to show for that halving, e.g. "Halving – Apr 2028")
    """

    if "month" not in df.columns or "btc_mined_month" not in df.columns:
        raise ValueError("DataFrame must contain 'month' and 'btc_mined_month' columns")

    df_plot = df.sort_values("month").copy()
    df_plot["month"] = pd.to_datetime(df_plot["month"])

    if show_cumulative and "btc_cumulative" not in df_plot.columns:
        df_plot["btc_cumulative"] = df_plot["btc_mined_month"].cumsum()

    btc_orange = getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A")

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["btc_mined_month"],
            mode="lines",
            name="BTC mined / month",
            line=dict(color=btc_orange),
            yaxis="y",
            hovertemplate=(
                "<b>%{x|%b %Y}</b><br>BTC this month: %{y:.8f}<extra></extra>"
            ),
        )
    )

    if show_cumulative:
        fig.add_trace(
            go.Scatter(
                x=df_plot["month"],
                y=df_plot["btc_cumulative"],
                mode="lines",
                name="Cumulative BTC",
                line=dict(color=btc_orange, dash="dash"),
                yaxis="y2",
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>Cumulative BTC: %{y:.8f}<extra></extra>"
                ),
            )
        )

    if "is_halving" in df_plot.columns:
        halving_rows = df_plot[df_plot["is_halving"] == True]  # noqa: E712
        if not halving_rows.empty:
            for _, row in halving_rows.iterrows():
                month = row["month"]
                label = (
                    row.get("halving_label") or f"Halving – {month.strftime('%b %Y')}"
                )
                fig.add_shape(
                    type="line",
                    x0=month,
                    x1=month,
                    y0=0,
                    y1=1,
                    xref="x",
                    yref="paper",
                    line=dict(color=btc_orange, dash="dot", width=1),
                )
                fig.add_annotation(
                    x=month,
                    y=1,
                    xref="x",
                    yref="paper",
                    text=label,
                    showarrow=False,
                    font=dict(color=btc_orange),
                    yshift=8,
                )

    fig.update_layout(
        title=title,
        xaxis=dict(title=None),
        yaxis=dict(title="BTC mined / month", side="left"),
        yaxis2=dict(
            title="Cumulative BTC",
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=40, r=20, t=60, b=60),
    )

    st.plotly_chart(fig, width="stretch")


def render_cumulative_cashflow_chart(
    df: pd.DataFrame,
    initial_capex_gbp: float,
    title: str = "Cumulative cashflow & payback",
) -> tuple[Optional[int], Optional[str]]:
    """
    Plot cumulative net cashflow over time and highlight payback point.
    Expects:
      - month (datetime64[ns])
      - net_cashflow_gbp (float per month)
    initial_capex_gbp is treated as an upfront negative cashflow at t0.
    """
    if "month" not in df.columns or "net_cashflow_gbp" not in df.columns:
        raise ValueError(
            "DataFrame must contain 'month' and 'net_cashflow_gbp' columns"
        )

    df_plot = df.sort_values("month").reset_index(drop=True).copy()
    df_plot["month"] = pd.to_datetime(df_plot["month"])

    cumulative = []
    running_total = -float(initial_capex_gbp)
    for cf in df_plot["net_cashflow_gbp"]:
        running_total += cf
        cumulative.append(running_total)
    df_plot["cumulative_cashflow_gbp"] = cumulative

    payback_idx: Optional[int] = None
    for i, value in enumerate(df_plot["cumulative_cashflow_gbp"]):
        if value >= 0:
            payback_idx = i
            break

    payback_month = (
        df_plot.loc[payback_idx, "month"] if payback_idx is not None else None
    )
    payback_value = (
        df_plot.loc[payback_idx, "cumulative_cashflow_gbp"]
        if payback_idx is not None
        else None
    )

    btc_orange = getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A")
    net_green = "#2ca02c"

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["cumulative_cashflow_gbp"],
            mode="lines",
            name="Cumulative net cashflow (GBP)",
            line=dict(color=net_green, width=3),
            hovertemplate="Cumulative cashflow: £%{y:,.0f}<extra></extra>",
        )
    )

    fig.add_hline(
        y=0,
        line_width=0.75,
        line_dash="dash",
        line_color="rgba(0,0,0,0.2)",
        opacity=1.0,
    )

    if payback_month is not None:
        fig.add_shape(
            type="line",
            x0=payback_month,
            x1=payback_month,
            y0=0,
            y1=1,
            xref="x",
            yref="paper",
            line=dict(color=btc_orange, dash="dot", width=1),
        )
        fig.add_trace(
            go.Scatter(
                x=[payback_month],
                y=[payback_value],
                mode="markers",
                name="Payback point",
                marker=dict(color=btc_orange, size=9),
                hovertemplate=(
                    "<b>Payback</b><br>Month: %{x|%b %Y}<br>"
                    "Cumulative: £%{y:,.0f}<extra></extra>"
                ),
            )
        )
        months_to_payback = payback_idx + 1
        annotation_text = (
            f"Payback: {payback_month.strftime('%b %Y')} (month {months_to_payback})"
        )
        fig.add_annotation(
            x=payback_month,
            y=payback_value,
            xanchor="left",
            yanchor="bottom",
            text=annotation_text,
            showarrow=True,
            arrowhead=2,
            ax=20,
            ay=-30,
            bgcolor="rgba(255,255,255,0.8)",
        )

    fig.update_layout(
        title=title,
        xaxis=dict(title=""),
        yaxis=dict(title="Cumulative cashflow (GBP)"),
        hovermode="x unified",
        showlegend=True,
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        margin=dict(l=40, r=40, t=60, b=60),
    )

    st.plotly_chart(fig, width="stretch")

    if payback_month is not None:
        st.info(
            f"**Payback achieved in month {months_to_payback} "
            f"({payback_month.strftime('%b %Y')}).**"
        )
        return months_to_payback, payback_month.strftime("%b %Y")

    st.warning(
        "Payback is not reached within the modelled period "
        "(cumulative cashflow remains below £0)."
    )
    return None, None


def render_unified_forecast_chart(
    df: pd.DataFrame,
    show_btc_price: bool = True,
    title: str = "Unified BTC & Fiat forecast",
    halving_dates: list[pd.Timestamp] | None = None,
) -> None:
    """
    Unified view showing BTC mined (left axis) and revenue (right axis),
    with optional BTC price path. Accepts month, btc_mined or btc_mined_month,
    revenue_gbp, optional btc_price_gbp/usd, and halving markers.
    """
    df_plot = df.copy()
    if "btc_mined" not in df_plot.columns and "btc_mined_month" in df_plot.columns:
        df_plot["btc_mined"] = df_plot["btc_mined_month"]

    required = {"month", "btc_mined", "revenue_gbp"}
    missing = required - set(df_plot.columns)
    if missing:
        raise ValueError(f"Unified chart missing columns: {missing}")

    btc_orange = getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A")
    fiat_blue = getattr(settings, "FIAT_NEUTRAL_BLUE_HEX", "#1f77b4")

    df_plot = df_plot.sort_values("month").copy()
    df_plot["month"] = pd.to_datetime(df_plot["month"])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["btc_mined"],
            name="BTC mined / month",
            mode="lines",
            line=dict(color=btc_orange, width=1.5),
            yaxis="y1",
            hovertemplate="BTC mined: %{y:.8f} BTC<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["revenue_gbp"],
            name="Revenue / month (GBP)",
            mode="lines",
            line=dict(color=fiat_blue, width=2.8),
            yaxis="y2",
            hovertemplate="Revenue: £%{y:,.0f}<extra></extra>",
        )
    )

    price_col = None
    price_label = ""
    if "btc_price_gbp" in df_plot.columns:
        price_col = "btc_price_gbp"
        price_label = "BTC price (GBP)"
    elif "btc_price_usd" in df_plot.columns:
        price_col = "btc_price_usd"
        price_label = "BTC price (USD)"

    if show_btc_price and price_col:
        fig.add_trace(
            go.Scatter(
                x=df_plot["month"],
                y=df_plot[price_col],
                name=price_label,
                mode="lines",
                yaxis="y2",
                line=dict(color=btc_orange, width=1.2, dash="dot"),
                opacity=0.6,
                hovertemplate=f"{price_label}: %{{y:,.0f}}<extra></extra>",
            )
        )

    if "is_halving" in df_plot.columns:
        halvings = df_plot[df_plot["is_halving"] == True]  # noqa: E712
        for _, row in halvings.iterrows():
            month = row["month"]
            label = row.get("halving_label") or f"Halving – {month.strftime('%b %Y')}"
            fig.add_shape(
                type="line",
                x0=month,
                x1=month,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color=btc_orange, dash="dot", width=1),
            )
            fig.add_annotation(
                x=month,
                y=1,
                xref="x",
                yref="paper",
                text=label,
                showarrow=False,
                font=dict(color=btc_orange),
                yshift=8,
            )
    elif halving_dates:
        for h in pd.to_datetime(halving_dates):
            label = f"Halving – {h.strftime('%b %Y')}"
            fig.add_shape(
                type="line",
                x0=h,
                x1=h,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color=btc_orange, dash="dot", width=1),
            )
            fig.add_annotation(
                x=h,
                y=1,
                xref="x",
                yref="paper",
                text=label,
                showarrow=False,
                font=dict(color=btc_orange),
                yshift=8,
            )

    fig.update_layout(
        title=title,
        xaxis=dict(title=None, dtick="M3"),
        yaxis=dict(title="BTC mined / month", side="left", tickformat=".02f"),
        yaxis2=dict(
            title="Revenue & BTC price (GBP)",
            overlaying="y",
            side="right",
            tickprefix="£",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=60, r=70, t=60, b=60),
    )

    st.plotly_chart(fig, width="stretch")


def render_investment_summary(
    metrics,
    initial_capex_gbp: float,
    payback_month_index: Optional[int] = None,
    payback_month_label: Optional[str] = None,
) -> None:
    """Render a compact investment summary beneath cumulative cashflow."""
    st.subheader("Investment summary")

    cols = st.columns(4)

    with cols[0]:
        st.metric(
            label="CapEx (GBP)",
            value=f"£{initial_capex_gbp:,.0f}",
            help="Total upfront capital expenditure.",
        )

    with cols[1]:
        st.metric(
            label="Total net cash generated (after CapEx)",
            value=f"£{metrics.total_net_cash_gbp:,.0f}",
            help="Cumulative net cashflow minus initial CapEx.",
        )

    if payback_month_index is not None and payback_month_label is not None:
        payback_text = f"Month {payback_month_index} ({payback_month_label})"
    else:
        payback_text = "Not reached"

    with cols[2]:
        st.metric(
            label="Payback",
            value=payback_text,
            help="First month cumulative cashflow crosses zero.",
        )

    if getattr(metrics, "irr_annual", None) is not None:
        irr_pct = metrics.irr_annual * 100.0
        irr_value = f"{irr_pct:,.1f}%"
    else:
        irr_value = "N/A"

    with cols[3]:
        st.metric(
            label="IRR (annualised)",
            value=irr_value,
            help=(
                "IRR from monthly cashflows (CapEx at t0), annualised as "
                "(1+IRR_m)^12-1."
            ),
        )


def render_fiat_forecast_chart(
    df: pd.DataFrame,
    title: str = "Fiat forecast (monthly)",
    halving_dates: list[pd.Timestamp] | None = None,
) -> None:
    """
    Plotly fiat forecast:
      - Left axis: gross revenue (fiat)
      - Right axis: BTC price path
      - Halving markers optional.

    Expected df columns:
      - month: datetime64[ns]
      - revenue_gbp: float
      - btc_price_usd: float (or any fiat; axis title still references price)
    Optional:
      - power_cost_gbp: float
      - net_cashflow_gbp: float
    """

    required = {"month", "revenue_gbp", "btc_price_usd"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    fiat_blue = getattr(settings, "FIAT_NEUTRAL_BLUE_HEX", "#1f77b4")
    btc_orange = getattr(settings, "BITCOIN_ORANGE_HEX", "#F7931A")
    neutral_grey = getattr(settings, "BTC_BAR_GREY_HEX", "#cfd2d6")
    net_green = "#2ca02c"

    df_plot = df.sort_values("month").copy()
    df_plot["month"] = pd.to_datetime(df_plot["month"])

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["revenue_gbp"],
            mode="lines",
            name="Gross Revenue (GBP)",
            line=dict(color=fiat_blue, width=2.0, dash="solid"),
            yaxis="y",
            hovertemplate=(
                "<b>%{x|%b %Y}</b><br>Gross revenue: £%{y:,.0f}<extra></extra>"
            ),
        )
    )

    if "power_cost_gbp" in df_plot.columns:
        fig.add_trace(
            go.Scatter(
                x=df_plot["month"],
                y=df_plot["power_cost_gbp"],
                mode="lines",
                name="Power cost (GBP)",
                line=dict(color=neutral_grey, dash="dash", width=1.5),
                yaxis="y",
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>Power cost: £%{y:,.0f}<extra></extra>"
                ),
            )
        )

    if "net_cashflow_gbp" in df_plot.columns:
        fig.add_trace(
            go.Scatter(
                x=df_plot["month"],
                y=df_plot["net_cashflow_gbp"],
                mode="lines",
                name="Net cashflow (GBP)",
                line=dict(color=net_green, dash="solid", width=2.5),
                yaxis="y",
                hovertemplate=(
                    "<b>%{x|%b %Y}</b><br>Net cashflow: £%{y:,.0f}<extra></extra>"
                ),
            )
        )

    fig.add_trace(
        go.Scatter(
            x=df_plot["month"],
            y=df_plot["btc_price_usd"],
            mode="lines",
            name="BTC price (USD)",
            line=dict(color=btc_orange, width=1.5, dash="dot"),
            opacity=0.7,
            yaxis="y2",
            hovertemplate=("<b>%{x|%b %Y}</b><br>BTC price: $%{y:,.0f}<extra></extra>"),
        )
    )

    if halving_dates:
        for h in pd.to_datetime(halving_dates):
            label = f"Halving – {h.strftime('%b %Y')}"
            fig.add_shape(
                type="line",
                x0=h,
                x1=h,
                y0=0,
                y1=1,
                xref="x",
                yref="paper",
                line=dict(color=btc_orange, dash="dot", width=1),
            )
            fig.add_annotation(
                x=h,
                y=1,
                xref="x",
                yref="paper",
                text=label,
                showarrow=False,
                font=dict(color=btc_orange),
                yshift=8,
            )

    fig.update_layout(
        title=title,
        xaxis=dict(title=""),
        yaxis=dict(title="Gross Revenue (GBP)", side="left"),
        yaxis2=dict(
            title="BTC price (USD)",
            overlaying="y",
            side="right",
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.2,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=40, r=20, t=60, b=60),
    )

    st.plotly_chart(fig, width="stretch")
