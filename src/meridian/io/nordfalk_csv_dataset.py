"""CSV dataset for the Nordfalk SFTP drop.

The drop is produced by an SAP job that nobody at the client owns any more.
Its quirks, all of which this dataset absorbs:

  * semicolon separated, latin-1 encoded (a handful of store names carry the
    old ISO-8859-1 slashed o rather than UTF-8);
  * comma decimal separator on every numeric column;
  * dates as DD/MM/YYYY;
  * a trailing empty column on some files because the job writes a final
    separator;
  * "NULL" and "#I/T" (the Danish Excel n/a) as null markers;
  * headers occasionally arrive upper case after a system patch.
"""
import logging
from pathlib import PurePosixPath

import pandas as pd
from kedro.io.core import AbstractDataSet, DataSetError, get_filepath_str, get_protocol_and_path

logger = logging.getLogger(__name__)

NA_MARKERS = ["", "NULL", "null", "#I/T", "#N/A", "-", "."]

DEFAULT_LOAD_ARGS = {
    "sep": ";",
    "encoding": "latin-1",
    "decimal": ",",
    "na_values": NA_MARKERS,
    "keep_default_na": True,
}

DEFAULT_SAVE_ARGS = {
    "sep": ";",
    "encoding": "latin-1",
    "decimal": ",",
    "index": False,
}


class NordfalkCSVDataSet(AbstractDataSet):
    """Reads (and, rarely, writes) a file in the client's extract format."""

    def __init__(self, filepath, load_args=None, save_args=None, lowercase_headers=True):
        protocol, path = get_protocol_and_path(filepath)
        self._protocol = protocol
        self._filepath = PurePosixPath(path)
        self._lowercase_headers = lowercase_headers

        self._load_args = dict(DEFAULT_LOAD_ARGS)
        self._dayfirst = True
        if load_args:
            load_args = dict(load_args)
            # `dayfirst` is a read_csv argument only when dates are parsed, and
            # the extract dates are parsed downstream, so pull it out here.
            self._dayfirst = load_args.pop("dayfirst", True)
            self._load_args.update(load_args)

        self._save_args = dict(DEFAULT_SAVE_ARGS)
        if save_args:
            self._save_args.update(save_args)

    def _load(self):
        load_path = get_filepath_str(self._filepath, self._protocol)
        try:
            frame = pd.read_csv(load_path, **self._load_args)
        except UnicodeDecodeError:
            # Post-patch files from March 2023 onwards are UTF-8. The client
            # promised to make this consistent; it has not happened.
            logger.warning("Falling back to utf-8 for %s", load_path)
            args = dict(self._load_args)
            args["encoding"] = "utf-8"
            frame = pd.read_csv(load_path, **args)
        except Exception as exc:
            raise DataSetError("Could not read %s: %s" % (load_path, exc))

        frame = _drop_trailing_unnamed(frame)
        if self._lowercase_headers:
            frame.columns = [str(c).strip().lower() for c in frame.columns]
        frame.attrs = {"dayfirst": self._dayfirst, "source_path": load_path}
        return frame

    def _save(self, data):
        save_path = get_filepath_str(self._filepath, self._protocol)
        data.to_csv(save_path, **self._save_args)

    def _exists(self):
        import os

        return os.path.isfile(get_filepath_str(self._filepath, self._protocol))

    def _describe(self):
        return dict(
            filepath=self._filepath,
            protocol=self._protocol,
            load_args=self._load_args,
            save_args=self._save_args,
        )


def _drop_trailing_unnamed(frame):
    unnamed = [c for c in frame.columns if str(c).startswith("Unnamed:")]
    if unnamed:
        logger.info("Dropping trailing separator columns: %s", unnamed)
        frame = frame.drop(columns=unnamed)
    return frame
