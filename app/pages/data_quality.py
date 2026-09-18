"""Data quality page.

The client's data team look at this on Monday morning before they sign off
the drop. Thresholds were agreed in the sprint 7 workshop.
"""
import altair as alt
import pandas as pd
import streamlit as st

from components import loaders
from components.formatting import category_label, dkk, pct, region_label, week_display

# Agreed with client on 12/03: a week with more than 2% negative unit lines
# or more than 40 unmapped store lines is not signed off.
NEGATIVE_LINE_THRESHOLD = 0.02
UNMAPPED_STORE_THRESHOLD = 40


def render():
    st.header("Datakvalitet")

    report = loaders.load_data_quality()
    if report is None:
        loaders.missing_notice("data_quality_report")
        return

    checks = report.set_index("check")["value"].to_dict() if "check" in report.columns else {}

    left, middle, right = st.beta_columns(3)
    left.markdown("**Raekker i primary**")
    left.write(int(checks.get("primary_rows", 0)))
    middle.markdown("**Butikker**")
    middle.write(int(checks.get("stores", 0)))
    right.markdown("**Varer**")
    right.write(int(checks.get("articles", 0)))

    st.subheader("Kontroller")
    st.dataframe(report, height=320)

    _render_flags(checks)
    _render_coverage()
    _render_promo_checks()


def _render_flags(checks):
    negative_share = float(checks.get("negative_unit_share", 0.0))
    unmapped = int(checks.get("unmapped_store_lines", 0))

    if negative_share > NEGATIVE_LINE_THRESHOLD:
        st.error(
            "Returandel %s over graensen paa %s"
            % (pct(negative_share), pct(NEGATIVE_LINE_THRESHOLD))
        )
    else:
        st.success("Returandel %s inden for graensen" % pct(negative_share))

    if unmapped > UNMAPPED_STORE_THRESHOLD:
        st.error("%d linjer med ukendt butik" % unmapped)
    else:
        st.success("%d linjer med ukendt butik" % unmapped)


def _render_coverage():
    primary = loaders.load("demand_primary")
    if primary is None:
        loaders.missing_notice("demand_primary")
        return

    st.subheader("Daekning pr. uge")
    weekly = (
        primary.groupby("week_label")
        .agg(
            stores=("store_id", "nunique"),
            articles=("sku_id", "nunique"),
            rows=("units", "size"),
            net_value_dkk=("net_value_dkk", "sum"),
        )
        .reset_index()
    )
    weekly["uge"] = weekly["week_label"].map(week_display)

    chart = (
        alt.Chart(weekly)
        .mark_line(point=True)
        .encode(
            x=alt.X("week_label:O", title="Uge"),
            y=alt.Y("rows:Q", title="Raekker"),
            tooltip=["uge", "stores", "articles", "rows"],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)

    st.markdown("**Omsaetning pr. uge**")
    weekly["omsaetning"] = weekly["net_value_dkk"].map(dkk)
    st.dataframe(weekly[["uge", "stores", "articles", "rows", "omsaetning"]])

    missing = _missing_store_weeks(primary)
    if len(missing):
        st.warning("Butik/uge kombinationer uden salg: %d" % len(missing))
        st.dataframe(missing.head(50))


def _missing_store_weeks(primary):
    weeks = sorted(primary["week_label"].unique())
    stores = sorted(primary["store_id"].unique())
    expected = pd.MultiIndex.from_product([stores, weeks], names=["store_id", "week_label"])
    seen = primary.set_index(["store_id", "week_label"]).index.unique()
    gap = expected.difference(seen)
    frame = gap.to_frame(index=False)
    if len(frame):
        frame["region"] = frame["store_id"].astype(str).str[:2].map(region_label)
        frame["uge"] = frame["week_label"].map(week_display)
    return frame


def _render_promo_checks():
    promo = loaders.load("mart_promo_performance")
    if promo is None:
        return

    st.subheader("Kampagner uden baseline")
    if "baseline_units" not in promo.columns:
        st.info("Mart uden baseline kolonne, spring over.")
        return

    no_baseline = promo[promo["baseline_units"].isnull()]
    st.write("%d af %d kampagneuger" % (len(no_baseline), len(promo)))
    if len(no_baseline):
        table = no_baseline.head(50).copy()
        if "category_code" in table.columns:
            table["kategori"] = table["category_code"].astype(str).str.zfill(2).map(category_label)
        st.dataframe(table)
