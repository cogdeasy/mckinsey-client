"""Model evaluation nodes: accuracy pack for the weekly steerco."""
import logging

import numpy as np
import pandas as pd

from meridian.pipelines.model_evaluation import metrics
from meridian.utils import nordfalk_codes as codes

logger = logging.getLogger(__name__)


def score_test_set(test_set, demand_model, feature_spec):
    features = feature_spec["features"]
    matrix = test_set[features].fillna(0)
    raw = demand_model.predict(matrix)
    if feature_spec.get("log_target", True):
        prediction = np.expm1(raw)
    else:
        prediction = raw

    out = test_set.copy()
    out["forecast_units"] = np.clip(prediction, 0, None)
    # The client's incumbent rule is "same week last year", which is what the
    # forecast value add is measured against.
    out["naive_units"] = out.get("units_lag_52", out.get("units_lag_4"))
    out["abs_error"] = (out["forecast_units"] - out["units"]).abs()
    out["error"] = out["forecast_units"] - out["units"]
    logger.info(
        "Scored %d test rows, overall WAPE %.3f",
        len(out), metrics.wape(out["units"], out["forecast_units"])
    )
    return out


def accuracy_by_segment(test_predictions, params, segment):
    names = params["metrics"]
    min_actual = params.get("mape_min_actual_units", 5)
    rows = []
    for value, group in test_predictions.groupby(segment):
        row = {segment: value, "rows": len(group), "units": float(group["units"].sum())}
        row.update(
            metrics.compute(names, group["units"], group["forecast_units"], min_actual)
        )
        if group["naive_units"].notnull().any():
            row["fva"] = metrics.forecast_value_add(
                group["units"], group["forecast_units"], group["naive_units"].fillna(0)
            )
        rows.append(row)
    table = pd.DataFrame(rows).sort_values("units", ascending=False)
    return table.reset_index(drop=True)


def accuracy_by_region(test_predictions, params):
    table = accuracy_by_segment(test_predictions, params, "region_code")
    table["region_name"] = table["region_code"].map(codes.region_name)
    table["meets_threshold"] = table["wape"] <= params["acceptance_thresholds"]["wape_overall"]
    return table


def accuracy_by_category(test_predictions, params):
    table = accuracy_by_segment(test_predictions, params, "category_code")
    table["category_name"] = table["category_code"].map(codes.category_name)
    fresh = table["category_code"].isin(params.get("fresh_category_codes", []))
    threshold = np.where(
        fresh,
        params["acceptance_thresholds"]["wape_fresh"],
        params["acceptance_thresholds"]["wape_overall"],
    )
    table["threshold"] = threshold
    table["meets_threshold"] = table["wape"] <= table["threshold"]
    failing = table[~table["meets_threshold"]]
    if len(failing):
        logger.warning(
            "Categories above the agreed WAPE band: %s",
            ", ".join(failing["category_code"].astype(str))
        )
    return table


def rolling_backtest(features, demand_model, feature_spec, params, training_params):
    """Re-score the last N folds without refitting.

    A full refit per fold takes about 40 minutes on the engagement laptop, so
    the weekly pack uses the fixed model and only moves the window. The full
    refit backtest is run once per wave; see notebooks/03_backtest_refit.ipynb.
    """
    settings = params["backtest"]
    weeks = sorted(features["week_label"].unique())
    horizon = settings["fold_horizon_weeks"]
    step = settings["step_weeks"]

    rows = []
    for fold in range(settings["folds"]):
        end_index = len(weeks) - fold * step
        start_index = end_index - horizon
        if start_index < 1:
            break
        fold_weeks = weeks[start_index:end_index]
        fold_frame = features[features["week_label"].isin(fold_weeks)]
        if fold_frame.empty:
            continue
        matrix = fold_frame[feature_spec["features"]].fillna(0)
        raw = demand_model.predict(matrix)
        prediction = np.expm1(raw) if feature_spec.get("log_target", True) else raw
        prediction = np.clip(prediction, 0, None)
        row = {
            "fold": fold + 1,
            "weeks": "%s-%s" % (fold_weeks[0], fold_weeks[-1]),
            "rows": len(fold_frame),
        }
        row.update(
            metrics.compute(
                params["metrics"],
                fold_frame["units"],
                prediction,
                params.get("mape_min_actual_units", 5),
            )
        )
        rows.append(row)

    summary = pd.DataFrame(rows)
    if len(summary):
        logger.info("Backtest over %d folds, mean WAPE %.3f", len(summary), summary["wape"].mean())
    return summary


def feature_importance(demand_model, feature_spec, params):
    importances = getattr(demand_model, "feature_importances_", None)
    if importances is None:
        logger.warning("Estimator exposes no feature importances")
        return pd.DataFrame(columns=["feature", "importance", "rank"])

    n_features = getattr(demand_model, "n_features_", len(feature_spec["features"]))
    if n_features != len(feature_spec["features"]):
        logger.warning(
            "Model was fitted on %d features but the spec pins %d",
            n_features, len(feature_spec["features"])
        )

    table = pd.DataFrame(
        {"feature": feature_spec["features"], "importance": importances}
    ).sort_values("importance", ascending=False)
    table["rank"] = range(1, len(table) + 1)
    top_n = params.get("report_top_n_features", 25)
    return table.head(top_n).reset_index(drop=True)
