"""Display helpers. Danish number and week formatting."""

CLIENT_NAME = "Nordfalk Dagligvarer A/S"
CLIENT_CODE = "NFK"
FX_DKK_PER_EUR = 7.4436

REGION_NAMES = {
    "10": "Hovedstaden",
    "11": "Nordsjaelland",
    "20": "Sjaelland Syd",
    "30": "Fyn",
    "40": "Sydjylland",
    "50": "Midtjylland",
    "60": "Nordjylland",
    "90": "Depot",
}

CATEGORY_NAMES = {
    "10": "Frugt og groent",
    "20": "Drikkevarer",
    "30": "Mejeri",
    "40": "Brod og bageri",
    "50": "Kod og fjerkrae",
    "60": "Kolonial",
    "70": "Frost",
    "80": "Non food",
}


def danish_number(value, decimals=0):
    """1234567.8 -> '1.234.567,8'."""
    if value is None:
        return "-"
    text = "{:,.{d}f}".format(float(value), d=decimals)
    return text.replace(",", " ").replace(".", ",").replace(" ", ".")


def dkk(value, decimals=0):
    return "%s kr." % danish_number(value, decimals)


def eur(value_dkk, decimals=0):
    return "EUR %s" % danish_number(float(value_dkk) / FX_DKK_PER_EUR, decimals)


def pct(value, decimals=1):
    if value is None:
        return "-"
    return "%s%%" % danish_number(float(value) * 100.0, decimals)


def week_display(week_label):
    """202314 -> 'uge 14 / 2023'."""
    label = str(week_label)
    return "uge %s / %s" % (label[4:], label[:4])


def region_label(region_code):
    code = str(region_code).zfill(2)
    return "%s %s" % (code, REGION_NAMES.get(code, "Ukendt"))


def category_label(category_code):
    code = str(category_code).zfill(2)
    return "%s %s" % (code, CATEGORY_NAMES.get(code, "Ukendt"))
