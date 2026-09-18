"""Data engineering nodes: raw Nordfalk extracts -> primary demand frame.

The extract is weekly at store x article grain already, so most of the work
here is cleansing rather than aggregation:

  * the sales file is split per calendar year on the drop and has to be
    stacked before anything else;
  * store ids arrive as integers in some weeks and zero padded strings in
    others, depending on which job produced the file;
  * line values carry VAT and container deposit;
  * franchise and partner stores, depots, the HQ test store and the internal
    consumption categories all have to come out;
  * negative lines are returns booked against the original week.

Kept in one module on purpose: the client's platform team review this file
line by line at every release. -- SB
"""
import logging

import numpy as np
import pandas as pd

from meridian.utils import fiscal_calendar as fc
from meridian.utils import nordfalk_codes as codes
from meridian.utils import validation
from meridian.utils.holidays_dk import holiday_weeks, load_holidays

logger = logging.getLogger(__name__)

SALES_REQUIRED_COLUMNS = ["butik_id", "vare_nr", "dato", "antal", "omsaetning_dkk"]
PRIMARY_KEYS = ["store_id", "sku_id", "week_label"]


def stack_sales_extracts(sales_2022, sales_2023, params):
    """Stack the per calendar year sales files into one frame."""
    frames = [sales_2022, sales_2023]
    stacked = pd.DataFrame()
    for frame in frames:
        validation.check_required_columns(frame, SALES_REQUIRED_COLUMNS, "sales extract")
        stacked = stacked.append(frame, ignore_index=True)

    rename = dict(params["column_map"])
    stacked = stacked.rename(columns=rename)

    # `uge` is the client's own week label; trust it over re-deriving from the
    # date, because the date column is the Monday of the *delivery* week on
    # lines that were re-booked after a system outage.
    if "uge" in stacked.columns:
        stacked["week_label"] = stacked["uge"].astype(str).str.zfill(6)
        stacked = stacked.drop(columns=["uge"])
    else:
        parsed = pd.to_datetime(stacked["date"], format="%d/%m/%Y", errors="coerce")
        stacked["week_label"] = parsed.map(fc.week_label)

    stacked["date"] = pd.to_datetime(stacked["date"], format="%d/%m/%Y", errors="coerce")
    stacked["store_id"] = stacked["store_id"].astype(str).str.strip().str.zfill(4)
    stacked["sku_id"] = stacked["sku_id"].map(codes.normalise_sku)
    stacked["promo_code"] = stacked["promo_code"].fillna("").astype(str).str.upper()
    stacked["deposit_type"] = stacked.get("deposit_type", "").fillna("").astype(str)

    logger.info(
        "Stacked %d sales rows covering %s - %s",
        len(stacked),
        stacked["week_label"].min(),
        stacked["week_label"].max(),
    )
    return stacked


def clean_store_master(store_master, params, scope):
    """Store master: drop depots, test stores and out of scope formats."""
    stores = store_master.rename(columns=params["column_map"]).copy()
    stores["store_id"] = stores["store_id"].astype(str).str.strip().str.zfill(4)

    valid = stores["store_id"].map(codes.is_valid_store_id)
    if (~valid).any():
        logger.warning("Dropping %d rows with malformed store ids", int((~valid).sum()))
    stores = stores[valid]

    stores["region_code"] = stores["store_id"].map(codes.region_of)
    stores["region_name"] = stores["region_code"].map(codes.region_name)
    stores["region_group"] = stores["region_code"].map(codes.region_group)
    stores["store_format"] = stores["store_format"].astype(str).str.upper().str.strip()
    stores["opened_on"] = pd.to_datetime(
        stores["opened_on"], format="%d/%m/%Y", errors="coerce"
    )
    stores["sales_area_sqm"] = pd.to_numeric(stores["sales_area_sqm"], errors="coerce")

    is_depot = stores["store_id"].map(codes.is_depot)
    is_test = stores["store_id"].map(codes.is_test_store)
    out_of_scope = stores["store_format"].isin(scope.get("excluded_store_formats", []))
    keep = ~(is_depot | is_test | out_of_scope)
    logger.info(
        "Store master: %d in scope, %d depots, %d test, %d out of scope formats",
        int(keep.sum()), int(is_depot.sum()), int(is_test.sum()), int(out_of_scope.sum()),
    )
    stores = stores[keep]

    if params.get("drop_closed_stores", True) and "status" in stores.columns:
        stores = stores[stores["status"].astype(str).str.upper() == "AABEN"]

    columns = [
        "store_id",
        "navn",
        "region_code",
        "region_name",
        "region_group",
        "store_format",
        "opened_on",
        "sales_area_sqm",
        "postcode",
    ]
    columns = [c for c in columns if c in stores.columns]
    return stores[columns].rename(columns={"navn": "store_name"}).reset_index(drop=True)


def clean_product_hierarchy(product_hierarchy, params, scope):
    """Article master: normalise codes and drop out of scope categories."""
    products = product_hierarchy.rename(columns=params["column_map"]).copy()
    products["sku_id"] = products["sku_id"].map(codes.normalise_sku)
    products["category_code"] = products["category_code"].astype(str).str.zfill(2)
    products["subcategory_code"] = products["subcategory_code"].astype(str).str.zfill(4)

    # A handful of lines were migrated under the wrong parent in 2019.
    derived_parent = products["subcategory_code"].map(codes.category_of)
    mismatch = derived_parent != products["category_code"]
    if mismatch.any():
        logger.warning("Repointing %d articles to their subcategory parent", int(mismatch.sum()))
        products.loc[mismatch, "category_code"] = derived_parent[mismatch]

    products["category_name"] = products["category_code"].map(codes.category_name)
    products["is_fresh"] = products["category_code"].map(codes.is_fresh)
    products["deposit_type"] = products.get("pant_type", "").fillna("").astype(str).str.upper()
    products["case_pack"] = pd.to_numeric(products.get("kolli"), errors="coerce").fillna(1)

    excluded = scope.get("excluded_category_codes", [])
    products = products[~products["category_code"].isin(excluded)]

    columns = [
        "sku_id",
        "sku_description",
        "category_code",
        "category_name",
        "subcategory_code",
        "supplier_id",
        "deposit_type",
        "case_pack",
        "is_fresh",
    ]
    columns = [c for c in columns if c in products.columns]
    return products[columns].reset_index(drop=True)


def build_calendar(fiscal_calendar_raw):
    return fc.build_fiscal_calendar(fiscal_calendar_raw)


def clean_sales(sales_stacked, stores_cleaned, products_cleaned, params):
    """Cleanse the stacked sales frame and normalise line values."""
    sales = sales_stacked.copy()

    sales["units"] = pd.to_numeric(sales["units"], errors="coerce").fillna(0)
    sales["gross_value_dkk"] = pd.to_numeric(sales["gross_value_dkk"], errors="coerce")

    before = len(sales)
    sales = sales[sales["store_id"].isin(stores_cleaned["store_id"])]
    sales = sales[sales["sku_id"].isin(products_cleaned["sku_id"])]
    logger.info("Dropped %d rows for out of scope stores/articles", before - len(sales))

    # Refurbishment blackouts: the stores traded but the weeks are not
    # representative and were excluded from the wave-2 accuracy pack.
    for exclusion in params.get("refurbishment_exclusions", []) or []:
        mask = (
            (sales["store_id"] == exclusion["store_id"])
            & (sales["week_label"] >= exclusion["from_week"])
            & (sales["week_label"] <= exclusion["to_week"])
        )
        if mask.any():
            logger.info(
                "Excluding %d rows for store %s (refurbishment)",
                int(mask.sum()), exclusion["store_id"],
            )
        sales = sales[~mask]

    negative_policy = params["outliers"].get("negative_units_policy", "zero")
    negatives = sales["units"] < 0
    if negatives.any():
        logger.info("%d negative lines (returns), policy=%s", int(negatives.sum()), negative_policy)
        if negative_policy == "zero":
            sales.loc[negatives, "units"] = 0
        elif negative_policy == "drop":
            sales = sales[~negatives]

    cap = params["outliers"].get("max_weekly_units")
    quantile = params["outliers"].get("units_upper_percentile")
    if quantile:
        upper = sales["units"].quantile(quantile)
        cap = min(cap, upper) if cap else upper
    if cap:
        clipped = int((sales["units"] > cap).sum())
        if clipped:
            logger.info("Winsorising %d rows above %.0f units", clipped, cap)
        sales["units"] = sales["units"].clip(upper=cap)

    deposit_lookup = products_cleaned.set_index("sku_id")["deposit_type"].to_dict()
    sales["deposit_type"] = sales["sku_id"].map(deposit_lookup).fillna("")
    sales["deposit_dkk"] = np.where(
        sales["units"] > 0,
        sales["deposit_type"].map(lambda t: codes.DEPOSIT_CLASSES.get(t, 0.0)) * sales["units"],
        0.0,
    )
    sales["net_value_dkk"] = (
        sales["gross_value_dkk"] - sales["deposit_dkk"]
    ) / (1.0 + codes.VAT_RATE)
    sales["net_value_eur"] = sales["net_value_dkk"] / codes.FX_DKK_PER_EUR
    sales["unit_price_dkk"] = np.where(
        sales["units"] > 0, sales["net_value_dkk"] / sales["units"], np.nan
    )

    sales["promo_flag"] = (sales["promo_code"].str.len() > 0).astype(int)
    sales["promo_weight"] = sales["promo_code"].map(codes.promo_weight)

    duplicates = validation.check_unique(sales, params["dedupe_keys"], "sales")
    if duplicates:
        sales = (
            sales.sort_values(["week_label", "gross_value_dkk"])
            .drop_duplicates(subset=params["dedupe_keys"], keep="last")
        )

    return sales.reset_index(drop=True)


def build_promo_flags(promo_calendar, params):
    """Explode the promo calendar to one row per article x week."""
    promos = promo_calendar.copy()
    promos["vare_nr"] = promos["vare_nr"].map(codes.normalise_sku)
    promos["start_dato"] = pd.to_datetime(
        promos["start_dato"], format="%d/%m/%Y", errors="coerce"
    )
    promos["slut_dato"] = pd.to_datetime(
        promos["slut_dato"], format="%d/%m/%Y", errors="coerce"
    )
    promos["rabat_pct"] = (
        promos["rabat_pct"].astype(str).str.replace(",", ".").astype(float) / 100.0
    )

    rows = []
    for _, promo in promos.iterrows():
        if pd.isnull(promo["start_dato"]) or pd.isnull(promo["slut_dato"]):
            continue
        week_start = promo["start_dato"]
        while week_start <= promo["slut_dato"]:
            rows.append(
                {
                    "sku_id": promo["vare_nr"],
                    "week_label": fc.week_label(week_start),
                    "store_group": str(promo["butik_gruppe"]).strip().upper(),
                    "promo_code": str(promo["kampagne_kode"]).strip().upper(),
                    "discount_depth": promo["rabat_pct"],
                    "leaflet_page": promo.get("avis_side"),
                }
            )
            week_start = week_start + pd.Timedelta(days=7)

    flags = pd.DataFrame(rows)
    if flags.empty:
        return flags
    flags["is_leaflet"] = (flags["promo_code"] == "AVIS").astype(int)
    flags = flags.drop_duplicates(subset=["sku_id", "week_label", "store_group"])
    logger.info("Promo calendar exploded to %d article-weeks", len(flags))
    return flags.reset_index(drop=True)


def assemble_primary(
    sales_cleaned,
    stores_cleaned,
    products_cleaned,
    promo_flags,
    fiscal_calendar,
    traffic,
    holidays,
    scope,
):
    """Join everything into the primary demand frame."""
    frame = sales_cleaned.merge(stores_cleaned, on="store_id", how="inner")
    frame = frame.merge(products_cleaned, on="sku_id", how="inner", suffixes=("", "_prod"))

    calendar = fiscal_calendar[
        ["week_label", "fiscal_year", "fiscal_period", "fiscal_week", "week_start", "is_period_end"]
    ]
    frame = frame.merge(calendar, on="week_label", how="left")
    missing_weeks = frame["fiscal_year"].isnull().sum()
    if missing_weeks:
        logger.warning(
            "%d rows have no fiscal calendar entry; the calendar file is refreshed "
            "by Finance every September", int(missing_weeks)
        )

    frame = _attach_promo_depth(frame, promo_flags)

    if traffic is not None and len(traffic):
        traffic = traffic.copy()
        traffic["butik_id"] = traffic["butik_id"].astype(str).str.zfill(4)
        traffic["uge_label"] = traffic["uge_label"].astype(str)
        frame = frame.merge(
            traffic.rename(columns={"butik_id": "store_id", "uge_label": "week_label",
                                    "kunder": "store_traffic"}),
            on=["store_id", "week_label"],
            how="left",
        )

    week_features = holiday_weeks(load_holidays(holidays))
    frame["holiday_features"] = frame["week_label"].map(
        lambda label: ",".join(sorted(week_features.get(label, [])))
    )
    frame["is_holiday_week"] = (frame["holiday_features"].str.len() > 0).astype(int)

    min_units = scope.get("min_units_per_week", 0)
    if min_units:
        frame = frame[(frame["units"] >= min_units) | (frame["promo_flag"] == 1)]

    frame = frame.sort_values(PRIMARY_KEYS).reset_index(drop=True)
    validation.check_unique(frame, PRIMARY_KEYS, "demand_primary", blocking=True)
    logger.info("Primary demand frame: %d rows, %d columns", len(frame), frame.shape[1])
    return frame


def mirror_primary_to_csv(demand_primary):
    """CSV mirror of the primary layer for the client's own QA scripts."""
    return demand_primary


def build_data_quality_report(sales_cleaned, stores_cleaned, products_cleaned, demand_primary):
    parts = [
        validation.summarise(sales_cleaned, "sales_cleaned"),
        validation.summarise(stores_cleaned, "stores_cleaned"),
        validation.summarise(products_cleaned, "products_cleaned"),
        validation.summarise(demand_primary, "demand_primary"),
    ]
    report = pd.DataFrame()
    for part in parts:
        report = report.append(part, ignore_index=True)

    coverage = (
        demand_primary.groupby(["region_code", "week_label"])["units"]
        .count()
        .reset_index()
        .rename(columns={"units": "rows"})
    )
    gaps = coverage[coverage["rows"] < coverage["rows"].median() * 0.5]
    for _, gap in gaps.iterrows():
        report = report.append(
            {
                "dataset": "demand_primary",
                "column": "coverage:%s/%s" % (gap["region_code"], gap["week_label"]),
                "dtype": "check",
                "rows": int(gap["rows"]),
                "nulls": 0,
                "null_pct": 0.0,
                "distinct": 0,
            },
            ignore_index=True,
        )
    return report


def _attach_promo_depth(frame, promo_flags):
    """Bring the planned discount depth onto the sales lines.

    The promo calendar is kept at store *group* level ("ALLE", "STORBY",
    "JYLLAND"), so the join has to resolve the group membership per store.
    """
    if promo_flags is None or promo_flags.empty:
        frame["discount_depth"] = 0.0
        frame["is_leaflet"] = 0
        return frame

    frame["store_group"] = frame["region_code"].map(codes.region_group)
    all_stores = promo_flags[promo_flags["store_group"] == "ALLE"].drop(
        columns=["store_group"]
    )
    grouped = promo_flags[promo_flags["store_group"] != "ALLE"]

    merged = frame.merge(
        all_stores[["sku_id", "week_label", "discount_depth", "is_leaflet"]],
        on=["sku_id", "week_label"],
        how="left",
    )
    merged = merged.merge(
        grouped[["sku_id", "week_label", "store_group", "discount_depth", "is_leaflet"]],
        on=["sku_id", "week_label", "store_group"],
        how="left",
        suffixes=("", "_grp"),
    )
    merged["discount_depth"] = merged["discount_depth"].fillna(
        merged["discount_depth_grp"]
    ).fillna(0.0)
    merged["is_leaflet"] = merged["is_leaflet"].fillna(
        merged["is_leaflet_grp"]
    ).fillna(0).astype(int)
    return merged.drop(columns=["discount_depth_grp", "is_leaflet_grp"])
