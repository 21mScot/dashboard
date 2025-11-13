# app.py

from __future__ import annotations

import streamlit as st

from src.ui.layout import render_dashboard


def main() -> None:
    st.set_page_config(
        page_title="Bitcoin Mining Feasibility Dashboard",
        layout="wide",
    )
    # This renders the whole app, including the top-level tabs
    # (Overview, Scenarios & Risk, Assumptions & Methodology).
    render_dashboard()


if __name__ == "__main__":
    main()
