"""Forecast explorer.

History from the primary layer plus the 13 week forward forecast, filtered
the way the category managers ask for it: region first, then category.
"""
import altair as alt
import pandas as pd
import streamlit as st

from components import loaders
from components.formatting import (
    CATEGORY_NAMES,
    REGION_NAMES,
    category_label,
    dkk,
    eur,
    week_display,
)


def render():
    st.header("Prognose")

    history = loaders.load("demand_primary")
    forecast = loaders.load("forecast_adjusted")
    if history is None:
        loaders.missing_notice("demand_primary")
        return
    if forecast is None:
        loaders.missing_notice("forecast_adjusted")
        return

    region, categories, show_eur = _filters(history)

    history_view = _filter(history, region, categories)
    forecast_view = _filter(forecast, region, categories)

    _headline(history_view, forecast_view, show_eur)
    _chart(history_view, forecast_view)
    _tables(forecast_view)


def _filters(history):
    regions = sorted(history["region_code"].astype(str).str.zfill(2).unique())
    left, middle, right = st.beta_columns([2, 3, 1])
    region = left.selectbox(
        "Region",
        ["Alle"] + regions,
        format_func=lambda code: code if code == "Alle" else "%s %s" % (code, REGION_NAMES.get(code, "")),
    )
    categories = middle.multiselect(
        "Kategori",
        sorted(history["category_code"].astype(str).str.zfill(2).unique()),
        format_func=category_label,
    )
    show_eur = right.checkbox("EUR", value=False)
    return region, categories, show_eur


def _filter(frame, region, categories):
    out = frame.copy()
    out["region_code"] = out["region_code"].astype(str).str.zfill(2)
    out["category_code"] = out["category_code"].astype(str).str.zfill(2)
    if region != "Alle":
        out = out[out["region_code"] == region]
    if categories:
        out = out[out["category_code"].isin(categories)]
    return out


def _headline(history, forecast, show_eur):
    last_13 = sorted(history["week_label"].unique())[-13:]
    recent = history[history["week_label"].isin(last_13)]

    actual_units = float(recent["units"].sum())
    forecast_units = float(forecast["forecast_units"].sum())
    actual_value = float(recent["net_value_dkk"].sum())
    forecast_value = float(forecast["forecast_value_dkk"].sum())

    money = eur if show_eur else dkk

    left, middle, right = st.beta_columns(3)
    left.markdown("**Faktisk, seneste 13 uger**")
    left.write("%s stk" % "{:,.0f}".format(actual_units).replace(",", "."))
    left.write(money(actual_value))
    middle.markdown("**Prognose, naeste 13 uger**")
    middle.write("%s stk" % "{:,.0f}".format(forecast_units).replace(",", "."))
    middle.write(money(forecast_value))
    right.markdown("**Udvikling**")
    if actual_units:
        right.write("%.1f%% stk" % ((forecast_units / actual_units - 1.0) * 100.0))
    if actual_value:
        right.write("%.1f%% vaerdi" % ((forecast_value / actual_value - 1.0) * 100.0))


def _chart(history, forecast):
    hist = (
        history.groupby("week_label")
        .agg(units=("units", "sum"))
        .reset_index()
        .assign(serie="Faktisk")
    )
    fcst = (
        forecast.groupby("week_label")
        .agg(units=("forecast_units", "sum"))
        .reset_index()
        .assign(serie="Prognose")
    )
    combined = pd.concat([hist.tail(52), fcst])
    combined["uge"] = combined["week_label"].map(week_display)

    chart = (
        alt.Chart(combined)
        .mark_line()
        .encode(
            x=alt.X("week_label:O", title="Uge"),
            y=alt.Y("units:Q", title="Stk"),
            color=alt.Color("serie:N", title=""),
            tooltip=["uge", "serie", "units"],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def _tables(forecast):
    st.subheader("Prognose pr. kategori")
    by_category = (
        forecast.groupby("category_code")
        .agg(
            stk=("forecast_units", "sum"),
            vaerdi_dkk=("forecast_value_dkk", "sum"),
            butikker=("store_id", "nunique"),
            varer=("sku_id", "nunique"),
        )
        .reset_index()
    )
    by_category["kategori"] = by_category["category_code"].map(
        lambda code: CATEGORY_NAMES.get(code, "Ukendt")
    )
    by_category["vaerdi"] = by_category["vaerdi_dkk"].map(dkk)
    st.dataframe(by_category[["category_code", "kategori", "stk", "vaerdi", "butikker", "varer"]])

    st.subheader("Top 25 butik/vare")
    top = (
        forecast.groupby(["store_id", "sku_id"])
        .agg(stk=("forecast_units", "sum"), vaerdi_dkk=("forecast_value_dkk", "sum"))
        .reset_index()
        .sort_values("vaerdi_dkk", ascending=False)
        .head(25)
    )
    top["vaerdi"] = top["vaerdi_dkk"].map(dkk)
    st.dataframe(top[["store_id", "sku_id", "stk", "vaerdi"]])
