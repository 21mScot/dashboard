# src/ui/daily_revenue.py

from __future__ import annotations

import streamlit as st


def render_daily_revenue(metrics) -> None:
    """
    Show daily BTC + revenue for the site.
    - If SEC fields exist on `metrics`, display real values.
    - If not, show a placeholder message.
    """

    # Graceful fallback if SEC fields aren't wired yet
    site_btc_per_day = getattr(metrics, "site_btc_per_day", None)
    per_asic_btc_per_day = getattr(metrics, "per_asic_btc_per_day", None)
    site_gross_rev_gbp = getattr(metrics, "site_gross_revenue_per_day_gbp", None)
    site_power_cost_gbp = getattr(metrics, "site_power_cost_per_day_gbp", None)
    site_net_rev_gbp = getattr(metrics, "site_net_revenue_per_day_gbp", None)

    st.markdown("### Daily BTC & revenue")

    if site_btc_per_day is None or site_gross_rev_gbp is None:
        st.info(
            "Daily BTC and revenue per ASIC / per site will appear here once the "
            "dashboard is wired up to the Site Economy Calculator (SEC) backend."
        )
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "BTC / ASIC / day",
            (
                f"{per_asic_btc_per_day:.6f} BTC"
                if per_asic_btc_per_day is not None
                else "—"
            ),
        )
        st.metric(
            "BTC / site / day",
            f"{site_btc_per_day:.6f} BTC",
        )

    with col2:
        st.metric(
            "Gross revenue / day",
            f"£{site_gross_rev_gbp:,.2f}",
            help="Estimated BTC value converted to GBP using the active BTC price.",
        )

    with col3:
        st.metric(
            "Power cost / day",
            f"£{site_power_cost_gbp:,.2f}",
        )
        st.metric(
            "Net revenue / day",
            f"£{site_net_rev_gbp:,.2f}",
            delta=f"£{site_net_rev_gbp:,.2f} net",
        )
