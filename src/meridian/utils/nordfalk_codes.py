"""Nordfalk master data codes.

Everything the asset needs to know about how Nordfalk number their stores,
regions and categories. The codes come from the client's SAP retail install
and are documented (badly) in NFK-MD-003.

The store id is four characters: two for the old amt (county) numbering that
Nordfalk never migrated away from, then a running number inside the region.
Depots share the numbering space and start with a 9.
"""
import re

STORE_ID_LENGTH = 4
STORE_ID_RE = re.compile(r"^[0-9]{4}$")
DEPOT_PREFIX = "9"
TEST_STORE_SUFFIX = "99"

REGION_NAMES = {
    "11": "Hovedstaden",
    "31": "Fyn",
    "42": "Midtjylland",
    "55": "Syddanmark",
    "62": "Nordjylland",
    "70": "Sjaelland Vest",
}

# Region groupings used in the weekly pack. "Storby" is Copenhagen plus Aarhus
# and is the grouping the commercial team steer on.
REGION_GROUPS = {
    "STORBY": ["11", "42"],
    "JYLLAND": ["42", "55", "62"],
    "OERNE": ["11", "31", "70"],
}

# Store formats. FRANCHISE and PARTNER stores report through the franchisee
# system and are out of scope for the forecast.
STORE_FORMATS = ["HYPER", "SUPER", "NAER", "FRANCHISE", "PARTNER", "DEPOT"]
OWNED_FORMATS = ["HYPER", "SUPER", "NAER"]

CATEGORY_NAMES = {
    "10": "Mejeri",
    "11": "Frugt og groent",
    "12": "Koed og fisk",
    "20": "Drikkevarer",
    "30": "Kolonial",
    "40": "Non food",
    "98": "Svind",
    "99": "Internt forbrug",
}

# Categories the replenishment team treat as fresh: short shelf life, daily
# delivery, and the ones the accuracy thresholds are relaxed for.
FRESH_CATEGORY_CODES = ["10", "11", "12"]

# Subcategory codes are the category code plus two digits. A handful of lines
# were migrated with the wrong parent in 2019 and are patched here rather than
# in the warehouse (client will not reopen the migration).
SUBCATEGORY_PARENT_OVERRIDES = {
    "1219": "12",
    "2013": "20",
    "3020": "30",
}

PROMO_MECHANICS = ["AVIS", "TILBUD", "3F2", "MP", "KUPON"]
PROMO_MECHANIC_WEIGHT = {
    "AVIS": 1.0,
    "TILBUD": 0.8,
    "3F2": 0.65,
    "MP": 0.5,
    "KUPON": 0.35,
}

# Deposit ("pant") classes and their value in DKK. Included in the gross line
# value on the extract, so it has to come off before any value based work.
DEPOSIT_CLASSES = {"A": 1.0, "B": 1.5, "C": 3.0}

VAT_RATE = 0.25
FX_DKK_PER_EUR = 7.4436


def is_valid_store_id(store_id):
    """True for a real, four digit Nordfalk store id."""
    if store_id is None:
        return False
    return bool(STORE_ID_RE.match(str(store_id).strip()))


def is_depot(store_id):
    return str(store_id).startswith(DEPOT_PREFIX)


def is_test_store(store_id):
    return str(store_id).endswith(TEST_STORE_SUFFIX)


def region_of(store_id):
    """Region code carried in the first two characters of the store id."""
    store_id = str(store_id).strip()
    if not is_valid_store_id(store_id):
        return None
    return store_id[:2]


def region_name(region_code):
    return REGION_NAMES.get(str(region_code), "Ukendt")


def region_group(region_code):
    for group, members in REGION_GROUPS.items():
        if str(region_code) in members:
            return group
    return "OEVRIGE"


def category_of(subcategory_code):
    """Parent category of a subcategory code."""
    code = str(subcategory_code).strip()
    if code in SUBCATEGORY_PARENT_OVERRIDES:
        return SUBCATEGORY_PARENT_OVERRIDES[code]
    return code[:2]


def category_name(category_code):
    return CATEGORY_NAMES.get(str(category_code), "Ukendt")


def is_fresh(category_code):
    return str(category_code) in FRESH_CATEGORY_CODES


def normalise_sku(vare_nr):
    """Article numbers are five digits, zero padded, sometimes exported as int."""
    text = str(vare_nr).strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text.zfill(5)


def promo_weight(kampagne_kode):
    if not kampagne_kode:
        return 0.0
    return PROMO_MECHANIC_WEIGHT.get(str(kampagne_kode).strip().upper(), 0.25)
