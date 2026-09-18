"""Meridian review app.

Runs on the analytics VM for the weekly review with the Nordfalk category
team. Reads the pipeline outputs off disk, nothing is recomputed here.

    streamlit run app/meridian_app.py --server.port 8502

Navigation is a sidebar radio rather than the pages/ folder convention: the
VM is pinned to streamlit 0.82 and multipage apps are not available there.
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from components import loaders  # noqa: E402
from components.formatting import CLIENT_NAME, dkk  # noqa: E402
from pages import (  # noqa: E402
    data_quality,
    forecast_explorer,
    model_performance,
    scenarios,
)

PAGES = {
    "Datakvalitet": data_quality,
    "Prognose": forecast_explorer,
    "Scenarier": scenarios,
    "Modelperformance": model_performance,
}


def main():
    st.set_page_config(
        page_title="Meridian - Nordfalk Dagligvarer",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.sidebar.title("Meridian")
    st.sidebar.caption("Nordfalk Dagligvarer A/S - NFK-2021-DEM")
    choice = st.sidebar.radio("Side", list(PAGES.keys()))

    st.sidebar.markdown("---")
    summary = loaders.load_forecast_summary()
    if summary is not None and len(summary):
        st.sidebar.markdown("**Seneste koersel**")
        st.sidebar.write("Uger: %s - %s" % (summary["week_label"].min(), summary["week_label"].max()))
        st.sidebar.write("Prognose: %s" % dkk(summary["forecast_value_dkk"].sum()))
    else:
        st.sidebar.info("Ingen prognose fundet. Koer kedro run --pipeline scoring.")

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "Tal er ekskl. moms og pant. Beloeb i DKK medmindre andet er angivet."
    )

    st.title("%s - ugentlig efterspoergselsprognose" % CLIENT_NAME)
    PAGES[choice].render()


if __name__ == "__main__":
    main()
