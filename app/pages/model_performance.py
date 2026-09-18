"""Model performance page.

WAPE is the headline the client signed up to: the wave-1 target is 28% at
store x article x week on the ambient categories and 35% on fresh.
"""
import altair as alt
import streamlit as st

from components import loaders
from components.formatting import category_label, pct, region_label, week_display

TARGET_WAPE_AMBIENT = 0.28
TARGET_WAPE_FRESH = 0.35
FRESH_CATEGORIES = ["10", "30", "40", "50"]


def render():
    st.header("Modelperformance")

    by_region, by_category = loaders.load_accuracy()
    predictions = loaders.load("test_predictions")

    if by_region is None or by_category is None:
        loaders.missing_notice("accuracy_by_region")
        return

    _headline(predictions)
    _by_segment(by_region, by_category)
    _backtest()
    _importance()


def _headline(predictions):
    if predictions is None:
        return
    actual = predictions["units"].sum()
    forecast = predictions["forecast_units"].sum()
    abs_error = (predictions["units"] - predictions["forecast_units"]).abs().sum()

    left, middle, right = st.beta_columns(3)
    left.markdown("**WAPE, testperiode**")
    left.write(pct(abs_error / actual if actual else 0))
    middle.markdown("**Bias**")
    middle.write(pct((forecast - actual) / actual if actual else 0))
    right.markdown("**Raekker i test**")
    right.write(len(predictions))


def _by_segment(by_region, by_category):
    st.subheader("Pr. region")
    region_view = by_region.copy()
    region_view["region"] = region_view["region_code"].astype(str).str.zfill(2).map(region_label)
    region_view["wape_vist"] = region_view["wape"].map(pct)
    st.dataframe(region_view)

    chart = (
        alt.Chart(region_view)
        .mark_bar()
        .encode(
            x=alt.X("region:N", title=""),
            y=alt.Y("wape:Q", title="WAPE"),
            tooltip=["region", "wape", "bias"],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Pr. kategori")
    category_view = by_category.copy()
    category_view["kategori"] = (
        category_view["category_code"].astype(str).str.zfill(2).map(category_label)
    )
    category_view["maal"] = category_view["category_code"].astype(str).str.zfill(2).map(
        lambda code: TARGET_WAPE_FRESH if code in FRESH_CATEGORIES else TARGET_WAPE_AMBIENT
    )
    category_view["over_maal"] = category_view["wape"] > category_view["maal"]
    category_view["wape_vist"] = category_view["wape"].map(pct)
    category_view["maal_vist"] = category_view["maal"].map(pct)
    st.dataframe(
        category_view[["category_code", "kategori", "wape_vist", "maal_vist", "over_maal"]]
    )

    over = category_view[category_view["over_maal"]]
    if len(over):
        st.warning("Kategorier over maal: %s" % ", ".join(over["kategori"].tolist()))
    else:
        st.success("Alle kategorier inden for maal")


def _backtest():
    backtest = loaders.load("backtest_summary")
    if backtest is None:
        return
    st.subheader("Rullende backtest")
    view = backtest.copy()
    if "week_label" in view.columns:
        view["uge"] = view["week_label"].map(week_display)
    st.dataframe(view)

    if "wape" in view.columns and "week_label" in view.columns:
        chart = (
            alt.Chart(view)
            .mark_line(point=True)
            .encode(
                x=alt.X("week_label:O", title="Uge"),
                y=alt.Y("wape:Q", title="WAPE"),
                tooltip=["uge", "wape"],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)


def _importance():
    importance = loaders.load("feature_importance")
    if importance is None:
        return
    st.subheader("Feature importance")
    top = importance.sort_values("importance", ascending=False).head(25)
    chart = (
        alt.Chart(top)
        .mark_bar()
        .encode(
            x=alt.X("importance:Q", title=""),
            y=alt.Y("feature:N", sort="-x", title=""),
            tooltip=["feature", "importance"],
        )
        .properties(height=480)
    )
    st.altair_chart(chart, use_container_width=True)
