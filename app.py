import streamlit as st

from src.core.live_data import LiveDataError, NetworkData, get_live_network_data
from src.ui.layout import render_dashboard


@st.cache_data(ttl=300)
def load_live_network_data() -> NetworkData | None:
    try:
        return get_live_network_data()
    except LiveDataError as e:
        st.warning(f"Could not load live network data, using defaults instead. ({e})")
        return None


def main() -> None:
    st.set_page_config(
        page_title="Bitcoin Mining ROI Dashboard",
        layout="wide",
    )
    render_dashboard()


if __name__ == "__main__":
    main()
