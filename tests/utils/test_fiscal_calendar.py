import datetime as dt

import pytest

from meridian.utils import fiscal_calendar as fc


def test_fiscal_year_starts_on_the_first_monday_of_october():
    assert fc.first_monday_of_october(2021) == dt.date(2021, 10, 4)
    assert fc.first_monday_of_october(2022) == dt.date(2022, 10, 3)


def test_fiscal_year_is_named_after_the_year_it_ends_in():
    assert fc.fiscal_year_of(dt.date(2022, 10, 3)) == 2023
    assert fc.fiscal_year_of(dt.date(2022, 9, 30)) == 2022


def test_fiscal_week_and_period():
    start = fc.first_monday_of_october(2021)
    assert fc.fiscal_week_of(start) == 1
    assert fc.fiscal_period_of(start) == 1
    assert fc.fiscal_week_of(start + dt.timedelta(days=7 * 4)) == 5
    assert fc.fiscal_period_of(start + dt.timedelta(days=7 * 4)) == 2
    # 4-4-5: period 3 is five weeks long, so week 13 is still period 3.
    assert fc.fiscal_period_of(start + dt.timedelta(days=7 * 12)) == 3
    assert fc.fiscal_period_of(start + dt.timedelta(days=7 * 13)) == 4


def test_week_label_round_trip():
    label = fc.week_label(dt.date(2022, 1, 5))
    assert label == "202201"
    assert fc.week_label_to_monday(label) == dt.date(2022, 1, 3)


def test_week_label_arithmetic_crosses_the_year_boundary():
    assert fc.week_label_add("202252", 1) == "202301"
    assert fc.week_label_diff("202301", "202252") == 1
    assert fc.week_label_diff("202210", "202201") == 9


def test_parse_client_date_is_day_first():
    assert fc.parse_client_date("03/01/2022") == dt.date(2022, 1, 3)
    assert fc.parse_client_date("12/11/2022") == dt.date(2022, 11, 12)


def test_parse_client_date_rejects_iso_input():
    with pytest.raises(ValueError):
        fc.parse_client_date("2022-01-03")


def test_build_fiscal_calendar(fiscal_calendar_raw):
    calendar = fc.build_fiscal_calendar(fiscal_calendar_raw)

    assert list(calendar.columns)[:5] == [
        "fiscal_year",
        "fiscal_period",
        "fiscal_week",
        "week_in_period",
        "week_label",
    ]
    assert calendar["week_label"].is_unique
    assert calendar["week_start"].is_monotonic_increasing

    period_one = calendar[calendar["fiscal_period"] == 1]
    assert len(period_one) == 4
    assert int(period_one["is_period_end"].sum()) == 1

    quarter_ends = calendar[calendar["is_quarter_end"]]
    assert set(quarter_ends["fiscal_period"]) <= {3, 6, 9, 12}
