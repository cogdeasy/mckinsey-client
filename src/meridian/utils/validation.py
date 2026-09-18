"""Light weight frame checks used by the data engineering pipeline.

Deliberately not a framework: the client's platform team vetoed bringing
great_expectations onto the engagement laptop image, so these are the checks
we run in-pipeline and surface on the data quality page.
"""
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class DataQualityError(Exception):
    """Raised when a check marked as blocking fails."""


def check_required_columns(frame, columns, name="frame"):
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataQualityError("%s is missing columns: %s" % (name, ", ".join(missing)))
    return True


def check_unique(frame, keys, name="frame", blocking=False):
    duplicated = frame.duplicated(subset=keys).sum()
    if duplicated:
        message = "%s has %d duplicate rows on %s" % (name, duplicated, keys)
        if blocking:
            raise DataQualityError(message)
        logger.warning(message)
    return duplicated


def check_not_null(frame, columns, name="frame", blocking=False):
    findings = {}
    for column in columns:
        nulls = int(frame[column].isnull().sum())
        if nulls:
            findings[column] = nulls
            message = "%s.%s has %d nulls" % (name, column, nulls)
            if blocking:
                raise DataQualityError(message)
            logger.warning(message)
    return findings


def check_value_range(frame, column, minimum=None, maximum=None, name="frame"):
    outside = 0
    if minimum is not None:
        outside += int((frame[column] < minimum).sum())
    if maximum is not None:
        outside += int((frame[column] > maximum).sum())
    if outside:
        logger.warning("%s.%s has %d values outside [%s, %s]",
                       name, column, outside, minimum, maximum)
    return outside


def summarise(frame, name):
    """One row per column, used to build the data quality report."""
    rows = []
    for column in frame.columns:
        series = frame[column]
        rows.append(
            {
                "dataset": name,
                "column": column,
                "dtype": str(series.dtype),
                "rows": len(series),
                "nulls": int(series.isnull().sum()),
                "null_pct": round(float(series.isnull().mean()), 4),
                "distinct": int(series.nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)
