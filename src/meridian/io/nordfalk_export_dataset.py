"""Forecast hand-off file for the Nordfalk replenishment system.

Layout is frozen by interface note NFK-IF-014:

  * fixed column order and upper case headers;
  * semicolon separated, latin-1, comma decimals, no thousands separator;
  * week as YYYYWW, dates (where present) as DD/MM/YYYY;
  * quantities as integers, values to two decimals;
  * CRLF line endings, because the loader on their side is a mainframe
    transfer job that rejects bare LF;
  * a trailer line "SLUT;<rowcount>" which their loader checks.

Changing any of this requires the client's integration team to re-test, which
takes a sprint. Do not "tidy" it.
"""
import logging
import os

from kedro.io.core import AbstractDataSet, DataSetError, get_filepath_str, get_protocol_and_path

logger = logging.getLogger(__name__)

INTERFACE_COLUMNS = [
    "BUTIK_ID",
    "VARE_NR",
    "UGE",
    "PROGNOSE_ANTAL",
    "PROGNOSE_VAERDI_DKK",
    "MODEL_VERSION",
]

TRAILER_TOKEN = "SLUT"
LINE_TERMINATOR = "\r\n"


class NordfalkExportDataSet(AbstractDataSet):
    def __init__(self, filepath, interface_ref="NFK-IF-014", columns=None, write_trailer=True):
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = path
        self._interface_ref = interface_ref
        self._columns = list(columns) if columns else list(INTERFACE_COLUMNS)
        self._write_trailer = write_trailer

    def _load(self):
        raise DataSetError(
            "%s is a write only hand-off file (%s)" % (self._filepath, self._interface_ref)
        )

    def _save(self, data):
        save_path = get_filepath_str(self._filepath, self._protocol)
        missing = [c for c in self._columns if c not in data.columns]
        if missing:
            raise DataSetError(
                "Export is missing interface columns %s (%s)" % (missing, self._interface_ref)
            )
        frame = data[self._columns].copy()
        frame["PROGNOSE_ANTAL"] = frame["PROGNOSE_ANTAL"].round(0).astype(int)
        frame["PROGNOSE_VAERDI_DKK"] = frame["PROGNOSE_VAERDI_DKK"].map(lambda v: "%.2f" % v)

        directory = os.path.dirname(save_path)
        if directory and not os.path.isdir(directory):
            os.makedirs(directory)

        body = frame.to_csv(sep=";", index=False, decimal=",", line_terminator=LINE_TERMINATOR)
        with open(save_path, "w", encoding="latin-1", errors="replace", newline="") as handle:
            handle.write(body)
            if self._write_trailer:
                handle.write("%s;%d%s" % (TRAILER_TOKEN, len(frame), LINE_TERMINATOR))
        logger.info("Wrote %d forecast rows to %s (%s)",
                    len(frame), save_path, self._interface_ref)

    def _exists(self):
        return os.path.isfile(get_filepath_str(self._filepath, self._protocol))

    def _describe(self):
        return dict(
            filepath=self._filepath,
            interface_ref=self._interface_ref,
            columns=self._columns,
        )
