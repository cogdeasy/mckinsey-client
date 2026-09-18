"""Thin cover on feature engineering.

TODO(JLB, sprint 18): the lag block is only smoke tested. Needs a proper
fixture with a full 53 week year before the FY25 refit.
"""
import pandas as pd

from meridian.pipelines.feature_engineering import nodes


def _panel():
    weeks = ["2022%02d" % week for week in range(1, 15)]
    rows = []
    for week in weeks:
        rows.append(
            {
                "store_id": "1101",
                "sku_id": "10023",
                "week_label": week,
                "units": 100 + int(week[-2:]),
                "net_value_dkk": 950.0,
                "unit_price_dkk": 9.5,
                "discount_depth": 0.0,
                "promo_flag": 0,
                "promo_code": "",
                "region_code": "11",
                "category_code": "10",
                "subcategory_code": "1004",
                "store_format": "SUPER",
                "sales_area_sqm": 1420.0,
                "is_fresh": True,
            }
        )
    return pd.DataFrame(rows)


def test_add_lag_features_produces_the_configured_lags():
    params = {
        "target_column": "units",
        "lags": [1, 2, 4],
        "rolling_windows": [4],
        "rolling_stats": ["mean"],
    }
    frame = nodes.add_lag_features(_panel(), params)

    assert "units_lag_1" in frame.columns
    assert "units_lag_4" in frame.columns
    assert "units_roll_mean_4" in frame.columns
    assert pd.isnull(frame["units_lag_1"].iloc[0])
    assert frame["units_lag_1"].iloc[1] == frame["units"].iloc[0]


def test_add_calendar_features_flags_the_dead_weeks():
    params = {
        "christmas_build_up_weeks": [49, 50, 51],
        "summer_holiday_weeks": [29, 30, 31],
        "holiday_features": ["jul", "paaske"],
    }
    frame = nodes.add_calendar_features(_panel(), params)

    assert frame["is_dead_week"].iloc[0] == 1
    assert frame["is_dead_week"].iloc[5] == 0
