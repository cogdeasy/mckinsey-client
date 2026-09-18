"""Shared fixtures.

The frames below are trimmed versions of the real Nordfalk extracts: same
column names, same Danish conventions (DD/MM/YYYY, comma decimals already
parsed, semicolon files read by the dataset class), same store and article
numbering.
"""
import pandas as pd
import pytest


# One rename map for every extract, as in parameters_data_engineering.yml.
COLUMN_MAP = {
    "butik_id": "store_id",
    "vare_nr": "sku_id",
    "dato": "date",
    "antal": "units",
    "omsaetning_dkk": "gross_value_dkk",
    "kampagne_kode": "promo_code",
    "type": "store_format",
    "key": "source_key",
    "pant_type": "deposit_type",
    "vare_tekst": "sku_description",
    "kategori_kode": "category_code",
    "underkategori": "subcategory_code",
    "leverandoer_nr": "supplier_id",
    "region_kode": "region_code",
    "aabningsdato": "opened_on",
    "kvm": "sales_area_sqm",
    "postnr": "postcode",
}


@pytest.fixture
def de_params():
    return {
        "column_map": dict(COLUMN_MAP),
        "dedupe_keys": ["store_id", "sku_id", "week_label"],
        "drop_closed_stores": True,
        "outliers": {
            "negative_units_policy": "zero",
            "max_weekly_units": 5000,
            "units_upper_percentile": None,
        },
        "refurbishment_exclusions": [],
    }


@pytest.fixture
def store_params():
    return {"column_map": dict(COLUMN_MAP), "drop_closed_stores": True}


@pytest.fixture
def product_params():
    return {"column_map": dict(COLUMN_MAP)}


@pytest.fixture
def scope_params():
    return {
        "excluded_category_codes": ["98", "99"],
        "excluded_store_formats": ["FRANCHISE", "PARTNER"],
        "min_units_per_week": 0,
    }


@pytest.fixture
def sales_extract():
    """Two weeks of sales for three stores, as delivered by the client."""
    return pd.DataFrame(
        [
            ["1101", "10023", "03/01/2022", "202201", 330, 3918.75, "", "SUPER", "", "NFK|1101|10023|202201"],
            ["1101", "10047", "03/01/2022", "202201", 519, 4379.06, "AVIS", "SUPER", "", "NFK|1101|10047|202201"],
            ["1101", "20114", "03/01/2022", "202201", 120, 1687.50, "", "SUPER", "C", "NFK|1101|20114|202201"],
            ["4201", "10023", "03/01/2022", "202201", 210, 2493.75, "", "NAER", "", "NFK|4201|10023|202201"],
            ["4201", "10023", "10/01/2022", "202202", -12, -142.50, "", "NAER", "", "NFK|4201|10023|202202"],
            ["9001", "10023", "03/01/2022", "202201", 900, 10687.50, "", "DEPOT", "", "NFK|9001|10023|202201"],
        ],
        columns=[
            "butik_id",
            "vare_nr",
            "dato",
            "uge",
            "antal",
            "omsaetning_dkk",
            "kampagne_kode",
            "type",
            "pant_type",
            "key",
        ],
    )


@pytest.fixture
def store_master():
    return pd.DataFrame(
        [
            ["1101", "Nordfalk Norrebro", "11", "SUPER", "14/08/1998", 1420, "2200", "AABEN"],
            ["4201", "Nordfalk Aarhus C", "42", "NAER", "01/02/2005", 780, "8000", "AABEN"],
            ["1199", "Nordfalk Testbutik", "11", "SUPER", "01/01/2015", 500, "2100", "AABEN"],
            ["9001", "Depot Koege", "70", "DEPOT", "01/01/1990", 12000, "4600", "AABEN"],
            ["5502", "Nordfalk Kolding Syd", "55", "FRANCHISE", "03/03/2010", 640, "6000", "AABEN"],
            ["6201", "Nordfalk Aalborg Vest", "62", "SUPER", "12/06/2001", 1100, "9000", "LUKKET"],
        ],
        columns=[
            "butik_id",
            "navn",
            "region_kode",
            "type",
            "aabningsdato",
            "kvm",
            "postnr",
            "status",
        ],
    )


@pytest.fixture
def product_hierarchy():
    return pd.DataFrame(
        [
            ["10023", "Mini maelk 0,5% 1 L", "10", "1004", "L0231", "", "STK", 12],
            ["10047", "Skummetmaelk 1 L", "10", "1004", "L0231", "", "STK", 12],
            ["20114", "Sodavand 1,5 L", "20", "2013", "L0884", "C", "STK", 6],
            ["99001", "Internt forbrug kantine", "99", "9901", "L9999", "", "STK", 1],
            # Migrated under the wrong parent in 2019, repointed by the asset.
            ["12300", "Hakket oksekoed 500 g", "11", "1219", "L0455", "", "STK", 8],
        ],
        columns=[
            "vare_nr",
            "vare_tekst",
            "kategori_kode",
            "underkategori",
            "leverandoer_nr",
            "pant_type",
            "enhed",
            "kolli",
        ],
    )


@pytest.fixture
def promo_calendar():
    return pd.DataFrame(
        [
            ["K04101", "10047", "ALLE", "03/01/2022", "09/01/2022", "AVIS", "25,00", 24],
            ["K04102", "20114", "JYLLAND", "03/01/2022", "16/01/2022", "TILBUD", "15,00", ""],
        ],
        columns=[
            "kampagne_id",
            "vare_nr",
            "butik_gruppe",
            "start_dato",
            "slut_dato",
            "kampagne_kode",
            "rabat_pct",
            "avis_side",
        ],
    )


@pytest.fixture
def fiscal_calendar_raw():
    rows = []
    week_start = pd.Timestamp("2021-10-04")
    fiscal_week = 1
    period = 1
    week_in_period = 1
    for _ in range(60):
        label = "%d%02d" % (week_start.isocalendar()[0], week_start.isocalendar()[1])
        rows.append(
            [
                2022,
                period,
                week_in_period,
                fiscal_week,
                label,
                week_start.strftime("%d/%m/%Y"),
                (week_start + pd.Timedelta(days=6)).strftime("%d/%m/%Y"),
            ]
        )
        length = [4, 4, 5][(period - 1) % 3]
        week_in_period += 1
        if week_in_period > length:
            week_in_period = 1
            period += 1
        fiscal_week += 1
        week_start = week_start + pd.Timedelta(days=7)
    return pd.DataFrame(
        rows,
        columns=[
            "fin_aar",
            "periode",
            "uge_i_periode",
            "fin_uge",
            "uge_label",
            "uge_start_dato",
            "uge_slut_dato",
        ],
    )


@pytest.fixture
def holidays_extract():
    return pd.DataFrame(
        [
            ["01/01/2022", "Nytaarsdag", "HELLIGDAG", "J"],
            ["14/04/2022", "Skaertorsdag", "HELLIGDAG", "J"],
            ["15/04/2022", "Langfredag", "HELLIGDAG", "J"],
            ["05/06/2022", "Grundlovsdag", "HALVDAG", "N"],
            ["24/12/2022", "Juleaftensdag", "HALVDAG", "N"],
        ],
        columns=["dato", "navn", "type", "lukkedag"],
    )


@pytest.fixture
def traffic():
    return pd.DataFrame(
        [
            ["1101", "202201", 4229],
            ["1101", "202202", 4110],
            ["4201", "202201", 2870],
            ["4201", "202202", 2933],
        ],
        columns=["butik_id", "uge_label", "kunder"],
    )
