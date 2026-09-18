"""Regenerate the anonymised sample extract under data/01_raw.

The real extract lands on the client SFTP drop every Friday night. This script
reproduces a small, scrambled slice of it (12 stores, 18 lines, FY22-FY23) so
that the pipelines can be run end to end off the repo without warehouse
access. Store names, article numbers and volumes are synthetic; the layout,
encoding, separators and column names are the client's.

Run with:  python tools/make_sample_extract.py

Do not point this at the real extract. -- SB, sprint 9
"""
import csv
import datetime as dt
import math
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, os.pardir, "data", "01_raw")
MARTS = os.path.join(RAW, "marts")

SEP = ";"
ENC = "latin-1"
DATE_FMT = "%d/%m/%Y"

VAT_RATE = 0.25
DEPOSIT_DKK = {"A": 1.0, "B": 1.5, "C": 3.0, "": 0.0}

STORES = [
    # butik_id, navn, region_kode, type, aabningsdato, kvm, postnr, status
    ("1101", "Nordfalk Norrebro", "11", "SUPER", "14/08/1998", 1420, "2200", "AABEN"),
    ("1102", "Nordfalk Osterbro", "11", "SUPER", "02/03/2004", 1180, "2100", "AABEN"),
    ("1103", "Nordfalk Amager Strand", "11", "NAER", "19/11/2011", 640, "2300", "AABEN"),
    ("1108", "Nordfalk Valby Torv", "11", "HYPER", "05/09/1989", 3350, "2500", "AABEN"),
    ("3104", "Nordfalk Odense C", "31", "SUPER", "21/04/2001", 1290, "5000", "AABEN"),
    ("3117", "Nordfalk Svendborg", "31", "NAER", "11/06/2015", 580, "5700", "AABEN"),
    ("3122", "Nordfalk Nyborg", "31", "FRANCHISE", "30/01/2018", 410, "5800", "AABEN"),
    ("4201", "Nordfalk Aarhus Bruuns", "42", "HYPER", "28/10/2003", 2980, "8000", "AABEN"),
    ("4205", "Nordfalk Risskov", "42", "SUPER", "07/07/2009", 1340, "8240", "AABEN"),
    ("4218", "Nordfalk Silkeborg Nord", "42", "SUPER", "16/02/2013", 1510, "8600", "AABEN"),
    ("5502", "Nordfalk Kolding Syd", "55", "SUPER", "23/05/2006", 1260, "6000", "AABEN"),
    ("5511", "Nordfalk Esbjerg Havn", "55", "PARTNER", "12/09/2019", 470, "6700", "AABEN"),
    ("9001", "Nordfalk Distributionscenter Vest", "42", "DEPOT", "01/01/1994", 18400, "8464", "AABEN"),
    ("1199", "Nordfalk Testbutik HQ", "11", "SUPER", "01/01/2020", 100, "2900", "LUKKET"),
]

PRODUCTS = [
    # vare_nr, vare_tekst, kategori_kode, underkategori, leverandoer_nr, pant_type, enhed, kolli
    ("10023", "Mini maelk 0,5% 1 L", "10", "1004", "L0231", "", "STK", 12),
    ("10047", "Skummetmaelk 1 L", "10", "1004", "L0231", "", "STK", 12),
    ("10112", "Yoghurt naturel 1 kg", "10", "1012", "L0231", "", "STK", 6),
    ("10310", "Smoer 200 g", "10", "1031", "L0244", "", "STK", 20),
    ("11020", "Bananer loese", "11", "1102", "L0410", "", "KG", 1),
    ("11085", "Agurk stk", "11", "1108", "L0417", "", "STK", 10),
    ("11142", "Danske aebler 1 kg", "11", "1114", "L0410", "", "KG", 6),
    ("12004", "Hakket oksekoed 8-12%", "12", "1200", "L0519", "", "STK", 8),
    ("12066", "Kyllingebryst 700 g", "12", "1206", "L0522", "", "STK", 6),
    ("12190", "Baconsnack 140 g", "12", "1219", "L0519", "", "STK", 12),
    ("20015", "Cola 1,5 L", "20", "2001", "L0733", "C", "STK", 6),
    ("20041", "Danskvand citrus 0,5 L", "20", "2004", "L0733", "A", "STK", 24),
    ("20088", "Pilsner 33 cl 6-pak", "20", "2008", "L0741", "B", "PAK", 4),
    ("20131", "Appelsinjuice 1 L", "20", "2013", "L0736", "C", "STK", 8),
    ("30012", "Hvedemel 2 kg", "30", "3001", "L0812", "", "STK", 10),
    ("30077", "Kaffe formalet 400 g", "30", "3007", "L0820", "", "STK", 12),
    ("30154", "Havregryn 1 kg", "30", "3015", "L0812", "", "STK", 10),
    ("30209", "Toiletpapir 8 rl", "30", "3020", "L0844", "", "PAK", 6),
    ("99001", "Internt forbrug kantine", "99", "9900", "L9999", "", "STK", 1),
]

BASE_PRICE = {
    "10023": 9.5, "10047": 9.0, "10112": 16.95, "10310": 21.5,
    "11020": 14.95, "11085": 8.95, "11142": 19.95,
    "12004": 32.0, "12066": 48.5, "12190": 18.0,
    "20015": 17.95, "20041": 6.5, "20088": 44.0, "20131": 14.5,
    "30012": 12.95, "30077": 42.0, "30154": 13.5, "30209": 29.95,
    "99001": 0.0,
}

BASE_UNITS = {
    "10023": 410, "10047": 260, "10112": 150, "10310": 120,
    "11020": 330, "11085": 190, "11142": 140,
    "12004": 175, "12066": 130, "12190": 95,
    "20015": 240, "20041": 300, "20088": 160, "20131": 110,
    "30012": 85, "30077": 130, "30154": 95, "30209": 120,
    "99001": 6,
}

STORE_SIZE_FACTOR = {
    "1101": 1.0, "1102": 0.92, "1103": 0.48, "1108": 1.85,
    "3104": 0.88, "3117": 0.41, "3122": 0.3,
    "4201": 1.6, "4205": 0.95, "4218": 1.02,
    "5502": 0.9, "5511": 0.35, "9001": 0.05, "1199": 0.02,
}

PROMO_MECHANICS = ["AVIS", "TILBUD", "3F2", "MP", "KUPON"]

HOLIDAYS = [
    ("01/01/2022", "Nytaarsdag", "HELLIGDAG", "J"),
    ("14/04/2022", "Skaertorsdag", "HELLIGDAG", "J"),
    ("15/04/2022", "Langfredag", "HELLIGDAG", "J"),
    ("18/04/2022", "2. paaskedag", "HELLIGDAG", "J"),
    ("13/05/2022", "Store Bededag", "HELLIGDAG", "J"),
    ("26/05/2022", "Kristi Himmelfartsdag", "HELLIGDAG", "J"),
    ("06/06/2022", "2. pinsedag", "HELLIGDAG", "J"),
    ("05/06/2022", "Grundlovsdag", "LUKKEDAG", "H"),
    ("24/12/2022", "Juleaftensdag", "LUKKEDAG", "H"),
    ("25/12/2022", "1. juledag", "HELLIGDAG", "J"),
    ("26/12/2022", "2. juledag", "HELLIGDAG", "J"),
    ("31/12/2022", "Nytaarsaftensdag", "LUKKEDAG", "H"),
    ("01/01/2023", "Nytaarsdag", "HELLIGDAG", "J"),
    ("06/04/2023", "Skaertorsdag", "HELLIGDAG", "J"),
    ("07/04/2023", "Langfredag", "HELLIGDAG", "J"),
    ("10/04/2023", "2. paaskedag", "HELLIGDAG", "J"),
    ("05/05/2023", "Store Bededag", "HELLIGDAG", "J"),
    ("18/05/2023", "Kristi Himmelfartsdag", "HELLIGDAG", "J"),
    ("29/05/2023", "2. pinsedag", "HELLIGDAG", "J"),
    ("05/06/2023", "Grundlovsdag", "LUKKEDAG", "H"),
    ("24/12/2023", "Juleaftensdag", "LUKKEDAG", "H"),
    ("25/12/2023", "1. juledag", "HELLIGDAG", "J"),
    ("26/12/2023", "2. juledag", "HELLIGDAG", "J"),
]

LAST_WEEK_2023 = 39


def mondays(year, last_week):
    """Mondays of ISO weeks 1..last_week of `year`."""
    out = []
    for week in range(1, last_week + 1):
        try:
            day = dt.date.fromisocalendar(year, week, 1)
        except AttributeError:  # python 3.7 on the old build agent
            day = dt.datetime.strptime("%d-W%02d-1" % (year, week), "%Y-W%W-%w").date()
        out.append((week, day))
    return out


def dkk(value):
    return ("%.2f" % value).replace(".", ",")


def promo_plan(rng):
    """One promo calendar row per (article, week block) that is on offer."""
    rows = []
    kampagne_id = 4100
    for year, last_week in ((2022, 52), (2023, LAST_WEEK_2023)):
        for week, monday in mondays(year, last_week):
            for vare_nr, _, kat, _, _, _, _, _ in PRODUCTS:
                if kat == "99":
                    continue
                if rng.random() > 0.11:
                    continue
                kampagne_id += 1
                mechanic = rng.choice(PROMO_MECHANICS)
                depth = rng.choice([0.10, 0.15, 0.20, 0.25, 0.33])
                rows.append(
                    {
                        "kampagne_id": "K%05d" % kampagne_id,
                        "vare_nr": vare_nr,
                        "butik_gruppe": rng.choice(["ALLE", "ALLE", "ALLE", "STORBY", "JYLLAND"]),
                        "start_dato": monday.strftime(DATE_FMT),
                        "slut_dato": (monday + dt.timedelta(days=6)).strftime(DATE_FMT),
                        "kampagne_kode": mechanic,
                        "rabat_pct": dkk(depth * 100),
                        "avis_side": str(rng.randint(1, 24)) if mechanic == "AVIS" else "",
                        "_week": "%d%02d" % (year, week),
                        "_depth": depth,
                    }
                )
    return rows


def store_in_group(butik_id, gruppe):
    if gruppe == "ALLE":
        return True
    if gruppe == "STORBY":
        return butik_id[:2] in ("11", "42")
    if gruppe == "JYLLAND":
        return butik_id[:2] in ("42", "55")
    return False


def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding=ENC, errors="replace") as fh:
        writer = csv.writer(fh, delimiter=SEP, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    print("wrote %-44s %6d rows" % (os.path.relpath(path), len(rows)))


def main():
    rng = random.Random(20211129)
    if not os.path.isdir(MARTS):
        os.makedirs(MARTS)

    promos = promo_plan(rng)
    promo_by_week = {}
    for row in promos:
        promo_by_week.setdefault((row["vare_nr"], row["_week"]), []).append(row)

    holiday_weeks = {}
    for datestr, navn, _kind, _closed in HOLIDAYS:
        day = dt.datetime.strptime(datestr, DATE_FMT).date()
        iso = day.isocalendar()
        holiday_weeks.setdefault("%d%02d" % (iso[0], iso[1]), []).append(navn)

    sales = {2022: [], 2023: []}
    price_rows = []
    stock_rows = []
    mart_rows = []
    traffic_rows = []

    seen_price = set()
    for year, last_week in ((2022, 52), (2023, LAST_WEEK_2023)):
        for week, monday in mondays(year, last_week):
            week_label = "%d%02d" % (year, week)
            for butik_id, _navn, _region, fmt, _open, _kvm, _post, status in STORES:
                if status == "LUKKET" and rng.random() > 0.2:
                    continue
                traffic_rows.append(
                    (
                        butik_id,
                        week_label,
                        int(4200 * STORE_SIZE_FACTOR[butik_id] * (1 + 0.05 * math.sin(week / 7.0))),
                    )
                )
                for vare_nr, _txt, kat, _sub, _lev, pant, _enhed, kolli in PRODUCTS:
                    if kat == "99" and rng.random() > 0.3:
                        continue
                    base = BASE_UNITS[vare_nr] * STORE_SIZE_FACTOR[butik_id]
                    seasonal = 1 + 0.12 * math.sin(2 * math.pi * (week - 6) / 52.0)
                    if kat in ("10", "11", "12") and week in (50, 51):
                        seasonal *= 1.45
                    if kat == "20" and week in (26, 27, 28, 29, 30):
                        seasonal *= 1.3
                    if week_label in holiday_weeks:
                        seasonal *= 1.09
                    trend = 1 + 0.0025 * ((year - 2022) * 52 + week)

                    price = BASE_PRICE[vare_nr]
                    mechanic = ""
                    depth = 0.0
                    for promo in promo_by_week.get((vare_nr, week_label), []):
                        if store_in_group(butik_id, promo["butik_gruppe"]):
                            mechanic = promo["kampagne_kode"]
                            depth = promo["_depth"]
                            break
                    uplift = 1.0
                    if mechanic:
                        uplift = 1 + depth * {"AVIS": 4.2, "TILBUD": 3.1, "3F2": 2.6,
                                              "MP": 1.9, "KUPON": 1.4}[mechanic]
                        price = round(price * (1 - depth), 2)

                    units = base * seasonal * trend * uplift * rng.uniform(0.86, 1.14)
                    units = int(max(0, round(units)))
                    if rng.random() < 0.004:
                        units = 0  # out of stock week
                    if rng.random() < 0.0015:
                        units = -abs(int(units * 0.1)) - 1  # returns booked negative

                    deposit = DEPOSIT_DKK[pant] * max(units, 0)
                    gross = units * price * (1 + VAT_RATE) + deposit

                    sales[year].append(
                        (
                            butik_id,
                            vare_nr,
                            monday.strftime(DATE_FMT),
                            week_label,
                            units,
                            dkk(gross),
                            mechanic,
                            fmt,
                            pant,
                            "NFK|%s|%s|%s" % (butik_id, vare_nr, week_label),
                        )
                    )

                    if week % 4 == 1:
                        stock_rows.append(
                            (butik_id, vare_nr, monday.strftime(DATE_FMT),
                             int(max(units, 0) * rng.uniform(0.2, 0.6)), kolli)
                        )

                    key = (vare_nr, butik_id, week_label)
                    if key not in seen_price and (week % 2 == 1 or mechanic):
                        seen_price.add(key)
                        price_rows.append(
                            (vare_nr, butik_id, monday.strftime(DATE_FMT),
                             dkk(BASE_PRICE[vare_nr]), dkk(price))
                        )

    for year in (2022, 2023):
        write_csv(
            os.path.join(RAW, "NF_SALG_UGE_%d.csv" % year),
            ["butik_id", "vare_nr", "dato", "uge", "antal", "omsaetning_dkk",
             "kampagne_kode", "type", "pant_type", "key"],
            sales[year],
        )

    write_csv(
        os.path.join(RAW, "NF_BUTIK_STAMDATA.csv"),
        ["butik_id", "navn", "region_kode", "type", "aabningsdato", "kvm", "postnr", "status"],
        STORES,
    )
    write_csv(
        os.path.join(RAW, "NF_VARE_HIERARKI.csv"),
        ["vare_nr", "vare_tekst", "kategori_kode", "underkategori", "leverandoer_nr",
         "pant_type", "enhed", "kolli"],
        PRODUCTS,
    )
    write_csv(
        os.path.join(RAW, "NF_KAMPAGNE_KALENDER.csv"),
        ["kampagne_id", "vare_nr", "butik_gruppe", "start_dato", "slut_dato",
         "kampagne_kode", "rabat_pct", "avis_side"],
        [(r["kampagne_id"], r["vare_nr"], r["butik_gruppe"], r["start_dato"], r["slut_dato"],
          r["kampagne_kode"], r["rabat_pct"], r["avis_side"]) for r in promos],
    )
    write_csv(
        os.path.join(RAW, "NF_PRIS_HISTORIK.csv"),
        ["vare_nr", "butik_id", "gyldig_fra", "normalpris", "salgspris"],
        price_rows,
    )
    write_csv(
        os.path.join(RAW, "NF_LAGER_BEHOLDNING.csv"),
        ["butik_id", "vare_nr", "dato", "beholdning", "kolli"],
        stock_rows,
    )
    write_csv(
        os.path.join(RAW, "helligdage_dk.csv"),
        ["dato", "navn", "type", "lukkedag"],
        HOLIDAYS,
    )
    write_fiscal_calendar()
    write_marts(sales, traffic_rows, promos)


def write_fiscal_calendar():
    """Nordfalk 4-4-5 calendar, fiscal year starts the first Monday of October."""
    rows = []
    for fiscal_year in (2022, 2023, 2024):
        start = dt.date(fiscal_year - 1, 10, 1)
        while start.weekday() != 0:
            start += dt.timedelta(days=1)
        week_index = 0
        for period in range(1, 13):
            weeks_in_period = [4, 4, 5][(period - 1) % 3]
            for week_in_period in range(1, weeks_in_period + 1):
                week_start = start + dt.timedelta(days=7 * week_index)
                week_end = week_start + dt.timedelta(days=6)
                iso = week_start.isocalendar()
                rows.append(
                    (
                        fiscal_year,
                        period,
                        week_in_period,
                        week_index + 1,
                        "%d%02d" % (iso[0], iso[1]),
                        week_start.strftime(DATE_FMT),
                        week_end.strftime(DATE_FMT),
                    )
                )
                week_index += 1
    write_csv(
        os.path.join(RAW, "NF_FINANSKALENDER.csv"),
        ["fin_aar", "periode", "uge_i_periode", "fin_uge", "uge_label",
         "uge_start_dato", "uge_slut_dato"],
        rows,
    )


def write_marts(sales, traffic_rows, promos):
    """Mirror of the nightly dbt export (see dbt/scripts/export_marts.sh).

    Regenerated here so the repo is self contained; in the engagement these
    three files are written by the warehouse job, not by this script.
    """
    product_by_nr = {p[0]: p for p in PRODUCTS}
    store_by_id = {s[0]: s for s in STORES}
    mart = []
    for year in (2022, 2023):
        for (butik_id, vare_nr, dato, uge, antal, oms, kode, fmt, pant, _key) in sales[year]:
            product = product_by_nr[vare_nr]
            store = store_by_id[butik_id]
            gross = float(oms.replace(",", "."))
            deposit = DEPOSIT_DKK[product[5]] * max(antal, 0)
            net = (gross - deposit) / (1 + VAT_RATE)
            mart.append(
                (
                    uge,
                    dt.datetime.strptime(dato, DATE_FMT).date().isoformat(),
                    butik_id,
                    store[2],
                    store[3],
                    vare_nr,
                    product[2],
                    product[3],
                    antal,
                    "%.2f" % net,
                    "%.2f" % gross,
                    kode,
                    1 if kode else 0,
                )
            )
    write_csv(
        os.path.join(MARTS, "mart_sales_weekly.csv"),
        ["uge_label", "uge_start_dato", "butik_id", "region_kode", "butik_type", "vare_nr",
         "kategori_kode", "underkategori", "antal", "nettoomsaetning_dkk",
         "bruttoomsaetning_dkk", "kampagne_kode", "kampagne_flag"],
        mart,
    )
    write_csv(
        os.path.join(MARTS, "mart_store_week_traffic.csv"),
        ["butik_id", "uge_label", "kunder"],
        traffic_rows,
    )
    perf = {}
    for row in mart:
        if not row[11]:
            continue
        key = (row[5], row[0], row[11])
        agg = perf.setdefault(key, [0, 0.0])
        agg[0] += row[8]
        agg[1] += float(row[9])
    write_csv(
        os.path.join(MARTS, "mart_promo_performance.csv"),
        ["vare_nr", "uge_label", "kampagne_kode", "antal", "nettoomsaetning_dkk"],
        [(k[0], k[1], k[2], v[0], "%.2f" % v[1]) for k, v in sorted(perf.items())],
    )


if __name__ == "__main__":
    main()
