"""Scoring pipeline nodes: 13 week forward forecast and the hand-off file.

The scoring frame is built by rolling the feature frame forward week by week.
Lags shorter than the horizon are filled recursively from the model's own
output, which is how the wave-1 model behaved and what the client's accuracy
history is measured against.

Manual uplifts from the category managers are applied last, after rounding,
because they are agreed as "add x% on the delivered number".
"""
import logging

import numpy as np
import pandas as pd

from meridian.utils import fiscal_calendar as fc
from meridian.utils import nordfalk_codes as codes
from meridian.utils.holidays_dk import CHRISTMAS_BUILD_UP_WEEKS, SUMMER_HOLIDAY_WEEKS

logger = logging.getLogger(__name__)

CARRY_FORWARD_COLUMNS = [
    "region_code",
    "region_group",
    "store_format",
    "category_code",
    "subcategory_code",
    "supplier_id",
    "case_pack",
    "is_fresh",
    "sales_area_sqm",
    "store_sqm_bucket",
    "region_code_te",
    "category_code_te",
    "subcategory_code_te",
    "store_format_te",
    "base_price_dkk",
    "list_price_dkk",
    "shelf_price_dkk",
    "log_base_price",
    "store_traffic",
]


def build_scoring_frame(features, promo_flags, params):
    """One row per store x article x future week."""
    horizon = params["horizon_weeks"]
    anchor = params.get("anchor_week") or str(features["week_label"].max())
    future_weeks = [fc.week_label_add(anchor, offset) for offset in range(1, horizon + 1)]
    logger.info("Scoring %s -> %s", future_weeks[0], future_weeks[-1])

    latest = (
        features.sort_values("week_label")
        .groupby(["store_id", "sku_id"], as_index=False)
        .last()
    )

    rows = []
    for week in future_weeks:
        block = latest.copy()
        block["week_label"] = week
        block["iso_week"] = int(week[4:])
        block["units"] = np.nan
        rows.append(block)
    frame = pd.concat(rows, ignore_index=True)

    frame["fiscal_week"] = frame["week_label"].map(
        lambda label: fc.fiscal_week_of(fc.week_label_to_monday(label))
    )
    frame["fiscal_period"] = frame["week_label"].map(
        lambda label: fc.fiscal_period_of(fc.week_label_to_monday(label))
    )
    frame["week_sin"] = np.sin(2 * np.pi * frame["iso_week"] / 52.0)
    frame["week_cos"] = np.cos(2 * np.pi * frame["iso_week"] / 52.0)
    frame["is_christmas_build_up"] = frame["iso_week"].isin(CHRISTMAS_BUILD_UP_WEEKS).astype(int)
    frame["is_summer_holiday"] = frame["iso_week"].isin(SUMMER_HOLIDAY_WEEKS).astype(int)

    frame = _attach_planned_promos(frame, promo_flags)
    for column in CARRY_FORWARD_COLUMNS:
        if column in frame.columns:
            frame[column] = frame.groupby(["store_id", "sku_id"])[column].ffill()

    return frame.sort_values(["week_label", "store_id", "sku_id"]).reset_index(drop=True)


def score_forecast(scoring_frame, demand_model, feature_spec):
    matrix = scoring_frame[feature_spec["features"]].fillna(0)
    raw = demand_model.predict(matrix)
    prediction = np.expm1(raw) if feature_spec.get("log_target", True) else raw

    out = scoring_frame.copy()
    out["forecast_units_raw"] = np.clip(prediction, 0, None)
    logger.info(
        "Forecast %d rows, %.0f units total",
        len(out), float(out["forecast_units_raw"].sum())
    )
    return out


def apply_business_rules(forecast_raw, params):
    """Manual uplifts, case pack rounding and the value conversion."""
    out = forecast_raw.copy()
    out["uplift_factor"] = 1.0

    for uplift in params.get("manual_uplifts", []) or []:
        mask = out["category_code"] == str(uplift["category_code"])
        if uplift.get("region_code"):
            mask = mask & (out["region_code"] == str(uplift["region_code"]))
        out.loc[mask, "uplift_factor"] = uplift["factor"]

    out["forecast_units"] = out["forecast_units_raw"] * out["uplift_factor"]

    if params.get("round_to_case_pack", True):
        case_pack = out.get("case_pack")
        if case_pack is None:
            case_pack = pd.Series(params.get("default_case_pack", 1), index=out.index)
        case_pack = case_pack.fillna(params.get("default_case_pack", 1)).replace(0, 1)
        out["forecast_units"] = (
            np.ceil(out["forecast_units"] / case_pack) * case_pack
        )

    price = out["shelf_price_dkk"].fillna(out["base_price_dkk"])
    out["forecast_value_dkk"] = out["forecast_units"] * price
    out["forecast_value_eur"] = out["forecast_value_dkk"] / codes.FX_DKK_PER_EUR
    return out


def run_scenarios(scoring_frame, demand_model, feature_spec, elasticity_model, params):
    """What-if scenarios for the commercial team.

    Volume response to a price move comes from the elasticity model, not from
    the demand model: the demand model has never seen a price change of the
    size the scenarios ask about.
    """
    models = elasticity_model["models"]
    fallback_level = elasticity_model.get("fallback_level", "category_code")

    base_matrix = scoring_frame[feature_spec["features"]].fillna(0)
    base_raw = demand_model.predict(base_matrix)
    base_units = np.clip(
        np.expm1(base_raw) if feature_spec.get("log_target", True) else base_raw, 0, None
    )

    rows = []
    for name, scenario in params["scenarios"].items():
        price_change = scenario.get("price_change_pct", 0.0)
        intensity = scenario.get("promo_intensity", 1.0)

        elasticities = scoring_frame.apply(
            lambda row: _elasticity_for(row, models, fallback_level), axis=1
        )
        volume_factor = np.power(1.0 + price_change, elasticities.fillna(-1.2))
        promo_factor = 1.0 + (intensity - 1.0) * scoring_frame["promo_flag"].fillna(0) * 0.35

        units = base_units * volume_factor * promo_factor
        price = (
            scoring_frame["shelf_price_dkk"].fillna(scoring_frame["base_price_dkk"])
            * (1.0 + price_change)
        )
        value = units * price

        rows.append(
            {
                "scenario": name,
                "price_change_pct": price_change,
                "promo_intensity": intensity,
                "units": float(np.nansum(units)),
                "value_dkk": float(np.nansum(value)),
                "value_eur": float(np.nansum(value)) / codes.FX_DKK_PER_EUR,
                "mean_elasticity": float(elasticities.mean()),
            }
        )

    table = pd.DataFrame(rows)
    baseline = table[table["scenario"] == "baseline"]
    if len(baseline):
        table["units_vs_baseline"] = table["units"] / float(baseline["units"].iloc[0]) - 1.0
        table["value_vs_baseline"] = table["value_dkk"] / float(baseline["value_dkk"].iloc[0]) - 1.0
    return table


def build_export(forecast_adjusted, params):
    """Assemble the NFK-IF-014 hand-off frame."""
    settings = params["export"]
    out = pd.DataFrame(
        {
            "BUTIK_ID": forecast_adjusted["store_id"].astype(str).str.zfill(4),
            "VARE_NR": forecast_adjusted["sku_id"].astype(str).str.zfill(5),
            "UGE": forecast_adjusted["week_label"].astype(str),
            "PROGNOSE_ANTAL": forecast_adjusted["forecast_units"].fillna(0),
            "PROGNOSE_VAERDI_DKK": forecast_adjusted["forecast_value_dkk"].fillna(0.0),
            "MODEL_VERSION": settings["model_version"],
        }
    )
    out = out[settings["columns"]]
    logger.info("Hand-off file prepared with %d rows", len(out))
    return out


def summarise_forecast(forecast_adjusted):
    summary = (
        forecast_adjusted.groupby(["week_label", "region_code", "category_code"])
        .agg(
            forecast_units=("forecast_units", "sum"),
            forecast_value_dkk=("forecast_value_dkk", "sum"),
            stores=("store_id", "nunique"),
            articles=("sku_id", "nunique"),
        )
        .reset_index()
    )
    summary["region_name"] = summary["region_code"].map(codes.region_name)
    summary["category_name"] = summary["category_code"].map(codes.category_name)
    return summary


def _attach_planned_promos(frame, promo_flags):
    if promo_flags is None or promo_flags.empty:
        frame["promo_flag"] = 0
        frame["discount_depth"] = 0.0
        return frame

    planned = promo_flags[promo_flags["store_group"] == "ALLE"]
    merged = frame.drop(columns=[c for c in ["discount_depth", "is_leaflet"] if c in frame.columns])
    merged = merged.merge(
        planned[["sku_id", "week_label", "discount_depth", "is_leaflet"]],
        on=["sku_id", "week_label"],
        how="left",
    )
    merged["discount_depth"] = merged["discount_depth"].fillna(0.0)
    merged["is_leaflet"] = merged["is_leaflet"].fillna(0).astype(int)
    merged["promo_flag"] = (merged["discount_depth"] > 0).astype(int)
    merged["discount_depth_actual"] = merged["discount_depth"]
    return merged


def _elasticity_for(row, models, fallback_level):
    key = (row.get("category_code"), row.get("region_code"))
    fitted = models.get(key)
    if fitted is None:
        fitted = models.get((row.get(fallback_level), None))
    if fitted is None:
        return np.nan
    return float(fitted.params.get("log_price", np.nan))
