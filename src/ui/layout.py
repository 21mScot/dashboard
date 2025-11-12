import streamlit as st


def render_dashboard() -> None:
    st.title("Bitcoin Mining Feasibility Dashboard")
    st.markdown(
        "Use this dashboard to explore site-specific mining economics, "
        "future BTC value, and CapEx/revenue sharing options."
    )

    st.info("This is the starter layout. We’ll add the real sections next.")
