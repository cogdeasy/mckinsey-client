"""Dataset for the client's fiscal calendar extract.

Kept separate from NordfalkCSVDataSet because the calendar file is the one
extract that is comma separated (it is maintained by hand in Finance and
exported from a different tool) and because it is validated on load: a
missing or duplicated week silently shifts every lag feature in the asset.
"""
import logging

import pandas as pd
from kedro.io.core import AbstractDataSet, DataSetError, get_filepath_str, get_protocol_and_path

logger = logging.getLogger(__name__)

EXPECTED_COLUMNS = [
    "fin_aar",
    "periode",
    "uge_i_periode",
    "fin_uge",
    "uge_label",
    "uge_start_dato",
    "uge_slut_dato",
]

WEEKS_PER_FISCAL_YEAR = 52


class FiscalCalendarDataSet(AbstractDataSet):
    def __init__(self, filepath, sep=";", strict=True):
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = path
        self._sep = sep
        self._strict = strict

    def _load(self):
        load_path = get_filepath_str(self._filepath, self._protocol)
        frame = pd.read_csv(load_path, sep=self._sep, dtype={"uge_label": str})
        frame.columns = [str(c).strip().lower() for c in frame.columns]

        missing = [c for c in EXPECTED_COLUMNS if c not in frame.columns]
        if missing:
            raise DataSetError(
                "Fiscal calendar %s is missing columns %s" % (load_path, missing)
            )

        counts = frame.groupby("fin_aar")["fin_uge"].count()
        short_years = counts[counts < WEEKS_PER_FISCAL_YEAR]
        if len(short_years) and self._strict:
            raise DataSetError(
                "Fiscal calendar %s has incomplete years: %s"
                % (load_path, list(short_years.index))
            )

        duplicated = frame.duplicated(subset=["fin_aar", "fin_uge"]).sum()
        if duplicated:
            logger.warning("Fiscal calendar has %d duplicated fiscal weeks", duplicated)
        return frame

    def _save(self, data):
        raise DataSetError("The fiscal calendar is client maintained and read only")

    def _exists(self):
        import os

        return os.path.isfile(get_filepath_str(self._filepath, self._protocol))

    def _describe(self):
        return dict(filepath=self._filepath, protocol=self._protocol, strict=self._strict)
