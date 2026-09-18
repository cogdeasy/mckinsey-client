"""Disk loaders for the review app.

Paths mirror the kedro catalog. They are repeated here rather than read from
the catalog because the app runs on the analytics VM where the asset is not
installed as a package (raised in sprint 10 retro, not fixed).
"""
import os

import pandas as pd
import streamlit as st

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PATHS = {
    "demand_primary": "data/03_primary/demand_primary.pq",
    "demand_features": "data/04_feature/demand_features.pq",
    "test_predictions": "data/07_model_output/test_predictions.pq",
    "elasticity_coefficients": "data/07_model_output/elasticity_coefficients.csv",
    "forecast_adjusted": "data/07_model_output/forecast_adjusted.pq",
    "forecast_summary": "data/08_reporting/forecast_summary.csv",
    "scenario_results": "data/08_reporting/scenario_results.csv",
    "accuracy_by_region": "data/08_reporting/accuracy_by_region.csv",
    "accuracy_by_category": "data/08_reporting/accuracy_by_category.csv",
    "backtest_summary": "data/08_reporting/backtest_summary.csv",
    "data_quality_report": "data/08_reporting/data_quality_report.csv",
    "feature_importance": "data/08_reporting/feature_importance.csv",
    "mart_sales_weekly": "data/01_raw/marts/mart_sales_weekly.csv",
    "mart_promo_performance": "data/01_raw/marts/mart_promo_performance.csv",
    "store_master": "data/01_raw/NF_BUTIK_STAMDATA.csv",
}


def _full_path(key):
    return os.path.join(REPO_ROOT, PATHS[key])


def _read(key):
    path = _full_path(key)
    if not os.path.exists(path):
        return None
    if path.endswith(".pq"):
        return pd.read_parquet(path)
    if key in ("mart_sales_weekly", "mart_promo_performance", "store_master"):
        # Client extracts and the mart dump share the Danish CSV dialect.
        return pd.read_csv(path, sep=";", decimal=",", encoding="latin-1")
    return pd.read_csv(path)


@st.cache(allow_output_mutation=True, show_spinner=False)
def load(key):
    return _read(key)


def load_forecast_summary():
    return load("forecast_summary")


def load_scenarios():
    return load("scenario_results")


def load_accuracy():
    return load("accuracy_by_region"), load("accuracy_by_category")


def load_data_quality():
    return load("data_quality_report")


def available(keys):
    return [key for key in keys if load(key) is not None]


def missing_notice(key):
    st.warning(
        "Filen %s mangler. Koer den relevante kedro pipeline foerst." % PATHS[key]
    )
