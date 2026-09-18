"""Danish holiday handling.

The `holidays` package covers the public holidays but not the two Nordfalk
care about most: Grundlovsdag (shops shut at 12:00, so the week reads as a
short week) and the three shopping days before Christmas, which drive the
biggest single demand spike of the year.

Store Bededag is still in here. It was abolished from 2024 but the history in
the extract has it, and the client asked us to keep modelling it until the
FY25 refit. -- JL, sprint 16
"""
import datetime as dt

HALF_DAYS = ["Grundlovsdag", "Juleaftensdag", "Nytaarsaftensdag"]

MOVEABLE_FEASTS = [
    "Skaertorsdag",
    "Langfredag",
    "2. paaskedag",
    "Store Bededag",
    "Kristi Himmelfartsdag",
    "2. pinsedag",
]

# Feature name per holiday, as referenced in parameters_feature_engineering.
HOLIDAY_FEATURE_MAP = {
    "Nytaarsdag": "nytaar",
    "Nytaarsaftensdag": "nytaar",
    "Skaertorsdag": "paaske",
    "Langfredag": "paaske",
    "2. paaskedag": "paaske",
    "Store Bededag": "store_bededag",
    "Kristi Himmelfartsdag": "kristi_himmelfart",
    "2. pinsedag": "pinse",
    "Grundlovsdag": "grundlovsdag",
    "Juleaftensdag": "jul",
    "1. juledag": "jul",
    "2. juledag": "jul",
}

# Weeks where the Danish industrial holiday empties the cities. Stores on the
# coast see the mirror image; the region factor picks that up.
SUMMER_HOLIDAY_WEEKS = [29, 30, 31]
CHRISTMAS_BUILD_UP_WEEKS = [49, 50, 51]
# Week 52 is a stub week in most years: two closed days and no leaflet.
DEAD_WEEKS = [52, 1]


def load_holidays(frame, date_format="%d/%m/%Y"):
    """Turn the helligdage_dk extract into a list of (date, feature) pairs."""
    pairs = []
    for _, row in frame.iterrows():
        day = dt.datetime.strptime(str(row["dato"]).strip(), date_format).date()
        feature = HOLIDAY_FEATURE_MAP.get(str(row["navn"]).strip())
        if feature is None:
            continue
        pairs.append((day, feature))
    return pairs


def holiday_weeks(pairs):
    """Map week label -> set of holiday features falling in that week."""
    weeks = {}
    for day, feature in pairs:
        iso = day.isocalendar()
        label = "%d%02d" % (iso[0], iso[1])
        weeks.setdefault(label, set()).add(feature)
    return weeks


def is_half_day(name):
    return str(name).strip() in HALF_DAYS


def trading_days_in_week(week_start, holiday_dates, closed_on_sunday=False):
    """Trading days in a week, counting half days as half a day."""
    total = 0.0
    for offset in range(7):
        day = week_start + dt.timedelta(days=offset)
        if closed_on_sunday and day.weekday() == 6:
            continue
        name = holiday_dates.get(day)
        if name is None:
            total += 1.0
        elif is_half_day(name):
            total += 0.5
    return total
