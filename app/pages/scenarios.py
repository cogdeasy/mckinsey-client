"""Scenario what-ifs.

The scenario table itself is produced by the scoring pipeline. This page
adds the interactive price move, which is applied here in the app using the
fitted elasticities rather than by re-running the pipeline.
"""
import altair as alt
import numpy as np
import streamlit as st

from components import loaders
from components.formatting import category_label, dkk, eur, pct

DEFAULT_ELASTICITY = -1.2
VAT_RATE = 0.25


def render():
    st.header("Scenarier")

    scenarios = loaders.load_scenarios()
    if scenarios is None:
        loaders.missing_notice("scenario_results")
        return

    st.subheader("Koerte scenarier")
    table = scenarios.copy()
    table["vaerdi"] = table["value_dkk"].map(dkk)
    table["vaerdi_eur"] = table["value_dkk"].map(eur)
    if "value_vs_baseline" in table.columns:
        table["vs baseline"] = table["value_vs_baseline"].map(pct)
    st.dataframe(table)

    _interactive()


def _interactive():
    st.subheader("Ad hoc prisaendring")

    forecast = loaders.load("forecast_adjusted")
    coefficients = loaders.load("elasticity_coefficients")
    if forecast is None:
        loaders.missing_notice("forecast_adjusted")
        return

    left, right = st.beta_columns([2, 2])
    price_change = left.slider(
        "Prisaendring", min_value=-0.15, max_value=0.15, value=0.0, step=0.01
    )
    category = right.selectbox(
        "Kategori",
        ["Alle"] + sorted(forecast["category_code"].astype(str).str.zfill(2).unique()),
        format_func=lambda code: code if code == "Alle" else category_label(code),
    )

    view = forecast.copy()
    view["category_code"] = view["category_code"].astype(str).str.zfill(2)
    if category != "Alle":
        view = view[view["category_code"] == category]

    elasticity = _elasticity_lookup(coefficients)
    view["elasticity"] = view["category_code"].map(elasticity).fillna(DEFAULT_ELASTICITY)
    view["scenario_units"] = view["forecast_units"] * np.power(
        1.0 + price_change, view["elasticity"]
    )
    # Values on this page are shown incl. VAT: the commercial team read them
    # against the shelf price, not against the P&L.
    view["scenario_value_dkk"] = (
        view["scenario_units"]
        * view["shelf_price_dkk"].fillna(view["base_price_dkk"])
        * (1.0 + price_change)
        * (1.0 + VAT_RATE)
    )
    view["baseline_value_dkk"] = (
        view["forecast_units"]
        * view["shelf_price_dkk"].fillna(view["base_price_dkk"])
        * (1.0 + VAT_RATE)
    )

    baseline_units = float(view["forecast_units"].sum())
    scenario_units = float(view["scenario_units"].sum())
    baseline_value = float(view["baseline_value_dkk"].sum())
    scenario_value = float(view["scenario_value_dkk"].sum())

    left, middle, right = st.beta_columns(3)
    left.markdown("**Stk**")
    left.write("%.0f -> %.0f" % (baseline_units, scenario_units))
    middle.markdown("**Vaerdi inkl. moms**")
    middle.write("%s -> %s" % (dkk(baseline_value), dkk(scenario_value)))
    right.markdown("**Effekt**")
    if baseline_value:
        right.write(pct(scenario_value / baseline_value - 1.0))

    by_category = (
        view.groupby("category_code")
        .agg(
            baseline_stk=("forecast_units", "sum"),
            scenarie_stk=("scenario_units", "sum"),
            baseline_vaerdi=("baseline_value_dkk", "sum"),
            scenarie_vaerdi=("scenario_value_dkk", "sum"),
            elasticitet=("elasticity", "mean"),
        )
        .reset_index()
    )
    by_category["kategori"] = by_category["category_code"].map(category_label)

    chart = (
        alt.Chart(by_category)
        .mark_bar()
        .encode(
            x=alt.X("kategori:N", title=""),
            y=alt.Y("scenarie_vaerdi:Q", title="Vaerdi, DKK"),
            tooltip=["kategori", "scenarie_stk", "elasticitet"],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)
    st.dataframe(by_category)


def _elasticity_lookup(coefficients):
    if coefficients is None or "category_code" not in coefficients.columns:
        return {}
    grouped = (
        coefficients.groupby(coefficients["category_code"].astype(str).str.zfill(2))[
            "elasticity"
        ]
        .mean()
        .to_dict()
    )
    return grouped
