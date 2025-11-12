import streamlit as st

from src.ui.layout import render_dashboard

def main() -> None:
    st.set_page_config(
        page_title="Bitcoin Mining ROI Dashboard",
        layout="wide",
    )
    render_dashboard()

if __name__ == "__main__":
    main()
