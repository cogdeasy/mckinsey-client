"""Nordfalk fiscal calendar.

Nordfalk run a 4-4-5 calendar. Fiscal year N starts on the first Monday of
October of calendar year N-1, so FY2023 starts on 03/10/2022. Periods are
numbered 1-12 and the fiscal week number runs 1-52 across the year. Every
53rd week (it happens roughly every six years) is folded into period 12; the
client's own BI does the same.

Week labels are calendar ISO labels, YYYYWW, because that is what the sales
extract carries. The mapping from label to fiscal week comes from
NF_FINANSKALENDER.csv, which the client refresh once a year in September.
"""
import datetime as dt

import pandas as pd

FISCAL_YEAR_START_MONTH = 10
PERIOD_PATTERN = [4, 4, 5]
WEEK_LABEL_FORMAT = "{year}{week:02d}"
CLIENT_DATE_FORMAT = "%d/%m/%Y"


def first_monday_of_october(calendar_year):
    day = dt.date(calendar_year, FISCAL_YEAR_START_MONTH, 1)
    while day.weekday() != 0:
        day += dt.timedelta(days=1)
    return day


def fiscal_year_of(day):
    """Fiscal year containing `day`."""
    day = _as_date(day)
    start_this_year = first_monday_of_october(day.year)
    if day >= start_this_year:
        return day.year + 1
    return day.year


def fiscal_week_of(day):
    """Fiscal week number 1-52 (53 in a long year)."""
    day = _as_date(day)
    start = first_monday_of_october(fiscal_year_of(day) - 1)
    return ((day - start).days // 7) + 1


def fiscal_period_of(day):
    week = fiscal_week_of(day)
    period = 1
    remaining = week
    while True:
        length = PERIOD_PATTERN[(period - 1) % 3]
        if remaining <= length:
            return min(period, 12)
        remaining -= length
        period += 1


def week_label(day):
    """Calendar ISO week label as used on the client extract, e.g. 202314."""
    day = _as_date(day)
    iso = day.isocalendar()
    return WEEK_LABEL_FORMAT.format(year=iso[0], week=iso[1])


def week_label_to_monday(label):
    """Monday of the calendar week behind a YYYYWW label."""
    label = str(label).strip()
    year = int(label[:4])
    week = int(label[4:])
    return dt.datetime.strptime("%d-W%02d-1" % (year, week), "%Y-W%W-%w").date()


def week_label_add(label, weeks):
    return week_label(week_label_to_monday(label) + dt.timedelta(days=7 * weeks))


def week_label_diff(label_a, label_b):
    """Whole weeks between two labels (a - b)."""
    return (week_label_to_monday(label_a) - week_label_to_monday(label_b)).days // 7


def parse_client_date(value):
    """Parse a date in the client's DD/MM/YYYY convention."""
    if isinstance(value, (dt.date, dt.datetime)):
        return _as_date(value)
    return dt.datetime.strptime(str(value).strip(), CLIENT_DATE_FORMAT).date()


def build_fiscal_calendar(raw_calendar):
    """Tidy the NF_FINANSKALENDER extract into the asset's calendar frame."""
    calendar = raw_calendar.copy()
    calendar.columns = [c.strip().lower() for c in calendar.columns]
    calendar["uge_label"] = calendar["uge_label"].astype(str).str.zfill(6)
    calendar["week_start"] = pd.to_datetime(
        calendar["uge_start_dato"], format=CLIENT_DATE_FORMAT
    )
    calendar["week_end"] = pd.to_datetime(
        calendar["uge_slut_dato"], format=CLIENT_DATE_FORMAT
    )
    calendar = calendar.rename(
        columns={
            "fin_aar": "fiscal_year",
            "periode": "fiscal_period",
            "uge_i_periode": "week_in_period",
            "fin_uge": "fiscal_week",
            "uge_label": "week_label",
        }
    )
    calendar["is_period_end"] = calendar["week_in_period"] == calendar.groupby(
        ["fiscal_year", "fiscal_period"]
    )["week_in_period"].transform("max")
    calendar["is_quarter_end"] = calendar["is_period_end"] & (
        calendar["fiscal_period"] % 3 == 0
    )
    keep = [
        "fiscal_year",
        "fiscal_period",
        "fiscal_week",
        "week_in_period",
        "week_label",
        "week_start",
        "week_end",
        "is_period_end",
        "is_quarter_end",
    ]
    return calendar[keep].sort_values("week_start").reset_index(drop=True)


def _as_date(value):
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime().date()
    return parse_client_date(value)
