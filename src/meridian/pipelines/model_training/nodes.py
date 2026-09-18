"""Model training nodes.

Two models are fitted:

  * the demand model, a gradient boosted regressor on log units, used for the
    13 week forecast;
  * a log-log price elasticity per category x region, used by the scenario
    page and by the commercial team's price pack.

The split is a straight time cut, never random: the client's validation pack
compares the last 13 fiscal weeks week by week.
"""
import importlib
import logging

import numpy as np
import pandas as pd
import statsmodels.api as sm

logger = logging.getLogger(__name__)

ID_COLUMNS = [
    "store_id",
    "sku_id",
    "week_label",
    "date",
    "week_start",
    "source_key",
    "store_name",
    "sku_description",
    "holiday_features",
    "promo_code",
    "store_group",
    "region_name",
    "category_name",
    "opened_on",
]

NON_FEATURE_COLUMNS = ID_COLUMNS + [
    "units",
    "gross_value_dkk",
    "net_value_dkk",
    "net_value_eur",
    "deposit_dkk",
    "deposit_type",
    "unit_price_dkk",
    "units_yoy_ratio",
]


def split_train_test(features, params):
    """Time based split on the calendar week label."""
    frame = features.sort_values(["week_label", "store_id", "sku_id"]).copy()
    weeks = sorted(frame["week_label"].unique())
    horizon = params["test_horizon_weeks"]
    if len(weeks) <= horizon + 4:
        raise ValueError(
            "Only %d weeks of history after warm up, need at least %d"
            % (len(weeks), horizon + 5)
        )
    cut_week = weeks[-horizon]
    train = frame[frame["week_label"] < cut_week]
    test = frame[frame["week_label"] >= cut_week]
    logger.info(
        "Train %d rows (< %s), test %d rows (>= %s)", len(train), cut_week, len(test), cut_week
    )
    return train.reset_index(drop=True), test.reset_index(drop=True)


def build_feature_spec(train_set, params):
    """Pin the feature list so training and scoring cannot drift apart."""
    blocked = set(params.get("feature_blocklist", []) or [])
    numeric = train_set.select_dtypes(include=[np.number])
    features = [
        column
        for column in numeric.columns
        if column not in NON_FEATURE_COLUMNS and column not in blocked
    ]
    spec = {
        "target": params["target_column"],
        "log_target": params.get("log_target", True),
        "features": sorted(features),
        "n_features": len(features),
        "trained_on_weeks": [
            str(train_set["week_label"].min()),
            str(train_set["week_label"].max()),
        ],
        "client_code": "NFK",
        "model_version": "meridian-2.4.1",
    }
    logger.info("Feature spec pinned with %d features", len(features))
    return spec


def train_demand_model(train_set, feature_spec, params):
    estimator = _load_estimator(params["estimator"])
    model = estimator(**params["estimator_params"])

    features = feature_spec["features"]
    matrix = train_set[features].fillna(0)
    target = train_set[feature_spec["target"]].astype(float)
    if feature_spec.get("log_target", True):
        target = np.log1p(target.clip(lower=0))

    weights = _sample_weights(train_set, params.get("sample_weighting", {}))
    model.fit(matrix, target, sample_weight=weights)
    logger.info(
        "Trained %s on %d rows, %d features",
        params["estimator"], len(matrix), len(features)
    )
    return model


def fit_elasticity(elasticity_features, params):
    """Log-log OLS per category x region with a category level fallback."""
    settings = params["elasticity"]
    frame = elasticity_features.copy()
    frame["discount_depth_actual"] = frame["discount_depth_actual"].clip(
        upper=settings.get("winsorise_discount_at", 0.6)
    )

    coefficients = []
    models = {}

    for (category, region), group in frame.groupby(["category_code", "region_code"]):
        if len(group) < settings["min_observations"]:
            continue
        fitted = _fit_log_log(group)
        if fitted is None:
            continue
        models[(category, region)] = fitted
        coefficients.append(
            {
                "level": "category_region",
                "category_code": category,
                "region_code": region,
                "elasticity": float(fitted.params.get("log_price", np.nan)),
                "promo_lift": float(fitted.params.get("promo_flag", np.nan)),
                "r_squared": float(fitted.rsquared),
                "observations": int(len(group)),
            }
        )

    fallback_level = settings.get("fallback_level", "category_code")
    for level_value, group in frame.groupby(fallback_level):
        fitted = _fit_log_log(group)
        if fitted is None:
            continue
        models[(level_value, None)] = fitted
        coefficients.append(
            {
                "level": fallback_level,
                "category_code": level_value,
                "region_code": None,
                "elasticity": float(fitted.params.get("log_price", np.nan)),
                "promo_lift": float(fitted.params.get("promo_flag", np.nan)),
                "r_squared": float(fitted.rsquared),
                "observations": int(len(group)),
            }
        )

    table = pd.DataFrame(coefficients)
    if len(table):
        table = table.sort_values(["level", "category_code", "region_code"])
        logger.info(
            "Fitted %d elasticity models, median elasticity %.2f",
            len(table), table["elasticity"].median()
        )
    return {"models": models, "fallback_level": fallback_level}, table.reset_index(drop=True)


def _fit_log_log(group):
    columns = ["log_price", "promo_flag", "is_leaflet"]
    columns = [c for c in columns if c in group.columns]
    design = sm.add_constant(group[columns].astype(float), has_constant="add")
    try:
        return sm.OLS(group["log_units"].astype(float), design, missing="drop").fit()
    except Exception as exc:  # singular design on very thin groups
        logger.warning("Elasticity fit failed (%d rows): %s", len(group), exc)
        return None


def _sample_weights(train_set, settings):
    if not settings:
        return None
    half_life = settings.get("recency_half_life_weeks")
    weights = np.ones(len(train_set), dtype=float)
    if half_life:
        weeks = train_set["week_label"].astype(str)
        latest = weeks.max()
        age = weeks.map(
            lambda label: (int(latest[:4]) - int(label[:4])) * 52
            + (int(latest[4:]) - int(label[4:]))
        )
        weights = weights * np.power(0.5, age.astype(float) / float(half_life))
    multiplier = settings.get("promo_week_multiplier")
    if multiplier and "promo_flag" in train_set.columns:
        weights = weights * np.where(train_set["promo_flag"] == 1, multiplier, 1.0)
    return weights


def _load_estimator(path):
    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)
