"""Feature engineering nodes.

Feature block owners (sprint 13 split):
    lags / rollings        - JL
    promo and leaflet      - SB
    calendar and holidays  - SB
    price and elasticity   - MK

Everything is at store x article x fiscal week grain. Lags are taken on the
calendar week label, not the fiscal week, because the fiscal calendar skips a
week every few years and a fiscal lag of 52 would then compare against the
wrong trading week.
"""
import logging

import numpy as np
import pandas as pd

from meridian.utils import fiscal_calendar as fc
from meridian.utils import nordfalk_codes as codes
from meridian.utils.holidays_dk import (
    CHRISTMAS_BUILD_UP_WEEKS,
    DEAD_WEEKS,
    SUMMER_HOLIDAY_WEEKS,
)

logger = logging.getLogger(__name__)

PANEL_KEYS = ["store_id", "sku_id"]
SORT_KEYS = ["store_id", "sku_id", "week_label"]


def build_panel(demand_primary, params):
    """Sorted, gap free panel per store x article."""
    frame = demand_primary.copy()
    frame["week_label"] = frame["week_label"].astype(str)
    frame = frame.sort_values(SORT_KEYS).reset_index(drop=True)

    weeks = sorted(frame["week_label"].unique())
    pairs = frame[PANEL_KEYS].drop_duplicates()
    logger.info("Panel: %d store-article pairs over %d weeks", len(pairs), len(weeks))

    skeleton = pairs.assign(_join=1).merge(
        pd.DataFrame({"week_label": weeks, "_join": 1}), on="_join"
    ).drop(columns="_join")

    panel = skeleton.merge(frame, on=SORT_KEYS, how="left")
    # Weeks with no line at all are genuine zero demand weeks (the article was
    # listed but did not sell), not missing data.
    panel["units"] = panel["units"].fillna(0)
    panel["promo_flag"] = panel["promo_flag"].fillna(0).astype(int)
    panel["discount_depth"] = panel["discount_depth"].fillna(0.0)
    for column in ["region_code", "store_format", "category_code", "subcategory_code"]:
        if column in panel.columns:
            panel[column] = panel.groupby(PANEL_KEYS)[column].transform(
                lambda series: series.ffill().bfill()
            )
    panel["fiscal_year"] = panel["fiscal_year"].ffill()
    panel["iso_week"] = panel["week_label"].str[4:].astype(int)
    return panel.sort_values(SORT_KEYS).reset_index(drop=True)


def add_lag_features(panel, params):
    frame = panel.copy()
    target = params["target_column"]
    grouped = frame.groupby(PANEL_KEYS)[target]
    for lag in params["lags"]:
        frame["units_lag_%d" % lag] = grouped.shift(lag)
    for window in params["rolling_windows"]:
        shifted = grouped.shift(1)
        for stat in params["rolling_stats"]:
            rolled = shifted.groupby([frame["store_id"], frame["sku_id"]]).rolling(
                window, min_periods=max(2, window // 2)
            )
            frame["units_roll_%s_%d" % (stat, window)] = (
                getattr(rolled, stat)().reset_index(level=[0, 1], drop=True)
            )
    frame["units_yoy_ratio"] = pd.np.where(
        frame.get("units_lag_52", pd.Series(np.nan, index=frame.index)).fillna(0) > 0,
        frame[target] / frame.get("units_lag_52", pd.Series(np.nan, index=frame.index)),
        np.nan,
    )
    return frame


def add_promo_features(frame, params):
    """Promo mechanic dummies plus lead/lag spill over."""
    out = frame.copy()
    mechanics = params["promo_mechanics"]
    out["promo_code"] = out["promo_code"].fillna("").astype(str).str.upper()
    for code, label in mechanics.items():
        out["promo_%s" % label] = (out["promo_code"] == code).astype(int)
    out["promo_weight"] = out["promo_code"].map(codes.promo_weight).fillna(0.0)

    grouped = out.groupby(PANEL_KEYS)["promo_flag"]
    for lead in range(1, params.get("promo_lead_weeks", 0) + 1):
        out["promo_lead_%d" % lead] = grouped.shift(-lead).fillna(0)
    for lag in range(1, params.get("promo_lag_weeks", 0) + 1):
        out["promo_lag_%d" % lag] = grouped.shift(lag).fillna(0)

    # Pantry loading: a deep offer last week suppresses this week.
    out["discount_depth_lag_1"] = (
        out.groupby(PANEL_KEYS)["discount_depth"].shift(1).fillna(0.0)
    )
    out["promo_streak"] = (
        out.groupby(PANEL_KEYS)["promo_flag"]
        .apply(lambda series: series.groupby((series != series.shift()).cumsum()).cumcount() + 1)
        .reset_index(level=[0, 1], drop=True)
        * out["promo_flag"]
    )
    return out


def add_calendar_features(frame, params):
    out = frame.copy()
    out["iso_week"] = out["week_label"].str[4:].astype(int)
    out["fiscal_week"] = out["week_label"].map(
        lambda label: fc.fiscal_week_of(fc.week_label_to_monday(label))
    )
    out["fiscal_period"] = out["week_label"].map(
        lambda label: fc.fiscal_period_of(fc.week_label_to_monday(label))
    )
    out["is_christmas_build_up"] = out["iso_week"].isin(
        params.get("christmas_build_up_weeks", CHRISTMAS_BUILD_UP_WEEKS)
    ).astype(int)
    out["is_summer_holiday"] = out["iso_week"].isin(
        params.get("summer_holiday_weeks", SUMMER_HOLIDAY_WEEKS)
    ).astype(int)
    out["is_dead_week"] = out["iso_week"].isin(DEAD_WEEKS).astype(int)

    holiday_column = out.get("holiday_features")
    if holiday_column is None:
        holiday_column = pd.Series("", index=out.index)
    for feature in params["holiday_features"]:
        out["hol_%s" % feature] = holiday_column.fillna("").str.contains(feature).astype(int)

    # Week 52/1 straddle the year end and behave as one long week; the client
    # reports them together in the Christmas pack.
    out["week_sin"] = np.sin(2 * np.pi * out["iso_week"] / 52.0)
    out["week_cos"] = np.cos(2 * np.pi * out["iso_week"] / 52.0)
    return out


def add_price_features(frame, price_history, params):
    """Shelf price, base price and discount depth."""
    out = frame.copy()
    prices = price_history.copy()
    prices["vare_nr"] = prices["vare_nr"].map(codes.normalise_sku)
    prices["butik_id"] = prices["butik_id"].astype(str).str.zfill(4)
    prices["gyldig_fra"] = pd.to_datetime(
        prices["gyldig_fra"], format="%d/%m/%Y", errors="coerce"
    )
    prices["week_label"] = prices["gyldig_fra"].map(fc.week_label)
    prices = prices.rename(
        columns={
            "vare_nr": "sku_id",
            "butik_id": "store_id",
            "normalpris": "list_price_dkk",
            "salgspris": "shelf_price_dkk",
        }
    )
    for column in ["list_price_dkk", "shelf_price_dkk"]:
        prices[column] = pd.to_numeric(
            prices[column].astype(str).str.replace(",", "."), errors="coerce"
        )

    out = out.merge(
        prices[["store_id", "sku_id", "week_label", "list_price_dkk", "shelf_price_dkk"]],
        on=["store_id", "sku_id", "week_label"],
        how="left",
    )
    out[["list_price_dkk", "shelf_price_dkk"]] = out.groupby(PANEL_KEYS)[
        ["list_price_dkk", "shelf_price_dkk"]
    ].fillna(method="pad")

    window = params["price"]["base_price_window_weeks"]
    out["base_price_dkk"] = (
        out.groupby(PANEL_KEYS)["list_price_dkk"]
        .rolling(window, min_periods=1)
        .median()
        .reset_index(level=[0, 1], drop=True)
    )
    out["price_ratio"] = out["shelf_price_dkk"] / out["base_price_dkk"]
    out["discount_depth_actual"] = (1.0 - out["price_ratio"]).clip(lower=0.0)
    if params["price"].get("log_transform", True):
        out["log_price"] = np.log(out["shelf_price_dkk"].replace(0, np.nan))
        out["log_base_price"] = np.log(out["base_price_dkk"].replace(0, np.nan))

    buckets = params["price"]["discount_depth_buckets"]
    out["discount_bucket"] = pd.cut(
        out["discount_depth_actual"], bins=buckets, include_lowest=True, labels=False
    ).fillna(0).astype(int)
    return out


def encode_categoricals(frame, params):
    """Target mean encoding for the high cardinality client codes."""
    out = frame.copy()
    target = params["target_column"]
    smoothing = params.get("target_encoding_smoothing", 20)
    prior = out[target].mean()

    for column in ["region_code", "category_code", "subcategory_code", "store_format"]:
        if column not in out.columns:
            continue
        stats = out.groupby(column)[target].agg(["mean", "count"])
        encoded = (stats["mean"] * stats["count"] + prior * smoothing) / (
            stats["count"] + smoothing
        )
        out["%s_te" % column] = out[column].map(encoded).fillna(prior)

    out["store_sqm_bucket"] = pd.cut(
        out.get("sales_area_sqm", pd.Series(np.nan, index=out.index)),
        bins=[0, 600, 1200, 2000, 100000],
        labels=False,
    ).fillna(-1).astype(int)
    out["is_fresh"] = out["category_code"].map(codes.is_fresh).astype(int)
    return out


def finalise_features(frame, params):
    out = frame.copy()
    drop_weeks = params.get("drop_first_n_weeks", 0)
    if drop_weeks:
        weeks = sorted(out["week_label"].unique())
        keep_from = weeks[min(drop_weeks, len(weeks) - 1)]
        before = len(out)
        out = out[out["week_label"] >= keep_from]
        logger.info("Dropped %d warm up rows before %s", before - len(out), keep_from)

    lag_columns = [c for c in out.columns if c.startswith("units_lag_")]
    out = out.dropna(subset=lag_columns[:1] or None)
    out = out.reset_index(drop=True)
    logger.info("Feature frame: %d rows, %d columns", len(out), out.shape[1])
    return out


def build_elasticity_frame(features, promo_performance, params):
    """Article x region frame for the log-log elasticity fit."""
    frame = features[features["units"] > 0].copy()
    frame["log_units"] = np.log(frame["units"])
    frame["log_price"] = np.log(frame["shelf_price_dkk"].replace(0, np.nan))
    frame = frame.dropna(subset=["log_units", "log_price"])

    if promo_performance is not None and len(promo_performance):
        perf = promo_performance.copy()
        perf["vare_nr"] = perf["vare_nr"].map(codes.normalise_sku)
        perf = perf.rename(
            columns={
                "vare_nr": "sku_id",
                "uge_label": "week_label",
                "antal": "promo_units_total",
                "nettoomsaetning_dkk": "promo_value_total",
            }
        )
        perf["week_label"] = perf["week_label"].astype(str)
        frame = frame.merge(
            perf[["sku_id", "week_label", "promo_units_total"]],
            on=["sku_id", "week_label"],
            how="left",
        )
        frame["promo_units_total"] = frame["promo_units_total"].fillna(0)

    keep = [
        "store_id",
        "sku_id",
        "week_label",
        "region_code",
        "category_code",
        "subcategory_code",
        "log_units",
        "log_price",
        "discount_depth_actual",
        "promo_flag",
        "is_leaflet",
        "iso_week",
        "units",
        "shelf_price_dkk",
        "base_price_dkk",
    ]
    keep = [c for c in keep if c in frame.columns]
    return frame[keep].reset_index(drop=True)
