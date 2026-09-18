"""File and key naming conventions on the Nordfalk drop.

Extract files are named NF_<DOMAIN>_<GRAIN>_<YYYY>[_UGE<WW>].csv. The weekly
sales file is split by calendar year, the master data files are not versioned
at all and are simply overwritten every Friday.

Source keys on the sales extract look like NFK|<butik>|<vare>|<uge>, which is
what the client's reconciliation team quote in tickets, so the asset keeps
them intact all the way through to the reporting layer.
"""
import re

FILE_PREFIX = "NF"
KEY_PREFIX = "NFK"
KEY_SEPARATOR = "|"

EXTRACT_FILE_RE = re.compile(
    r"^NF_(?P<domain>[A-Z]+)(?:_(?P<grain>UGE|DAG|MDR))?_(?P<year>\d{4})"
    r"(?:_UGE(?P<week>\d{2}))?\.csv$"
)

DOMAIN_TO_DATASET = {
    "SALG": "sales_weekly",
    "BUTIK": "store_master",
    "VARE": "product_hierarchy",
    "KAMPAGNE": "promo_calendar",
    "PRIS": "price_history",
    "LAGER": "stock_positions",
    "FINANSKALENDER": "fiscal_calendar_raw",
}

EXPORT_FILE_TEMPLATE = "NF_PROGNOSE_UGE.csv"
EXPORT_ARCHIVE_TEMPLATE = "NF_PROGNOSE_UGE_{week_label}.csv"


def parse_extract_filename(filename):
    match = EXTRACT_FILE_RE.match(filename.strip())
    if match is None:
        return None
    parts = match.groupdict()
    parts["dataset"] = DOMAIN_TO_DATASET.get(parts["domain"])
    return parts


def source_key(store_id, sku_id, week_label):
    return KEY_SEPARATOR.join([KEY_PREFIX, str(store_id), str(sku_id), str(week_label)])


def parse_source_key(key):
    parts = str(key).split(KEY_SEPARATOR)
    if len(parts) != 4 or parts[0] != KEY_PREFIX:
        raise ValueError("Unexpected source key layout: %s" % key)
    return {"store_id": parts[1], "sku_id": parts[2], "week_label": parts[3]}


def export_filename(week_label=None, archive=False):
    if archive:
        return EXPORT_ARCHIVE_TEMPLATE.format(week_label=week_label)
    return EXPORT_FILE_TEMPLATE
