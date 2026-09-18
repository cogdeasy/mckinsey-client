"""Dataset tests for the client extract dialect."""
import pandas as pd

from meridian.io.nordfalk_csv_dataset import NordfalkCSVDataSet

EXTRACT = (
    "BUTIK_ID;VARE_NR;DATO;ANTAL;OMSAETNING_DKK;KAMPAGNE_KODE;\n"
    "1101;10023;03/01/2022;330;3918,75;;\n"
    "1101;10047;03/01/2022;519;4379,06;AVIS;\n"
    "4201;10023;03/01/2022;NULL;2493,75;#I/T;\n"
)


def _write(tmp_path, text, encoding="latin-1"):
    path = tmp_path / "NF_SALG_UGE_2022.csv"
    path.write_bytes(text.encode(encoding))
    return str(path)


def test_reads_the_client_dialect(tmp_path):
    dataset = NordfalkCSVDataSet(filepath=_write(tmp_path, EXTRACT))
    frame = dataset.load()

    assert list(frame.columns) == [
        "butik_id",
        "vare_nr",
        "dato",
        "antal",
        "omsaetning_dkk",
        "kampagne_kode",
    ]
    assert frame["omsaetning_dkk"].iloc[0] == 3918.75
    assert pd.isnull(frame["antal"].iloc[2])
    assert pd.isnull(frame["kampagne_kode"].iloc[2])


def test_falls_back_to_utf8(tmp_path):
    text = EXTRACT.replace("Nordfalk", "Nordfalk")
    text = text + "1103;10023;03/01/2022;12;180,00;;\n"
    path = tmp_path / "NF_SALG_UGE_2023.csv"
    path.write_bytes(("butik_navn\nNordfalk N\u00f8rrebro \u2013 1\n").encode("utf-8"))

    dataset = NordfalkCSVDataSet(filepath=str(path))
    frame = dataset.load()

    assert frame["butik_navn"].iloc[0].startswith("Nordfalk N")


def test_headers_can_be_left_as_delivered(tmp_path):
    dataset = NordfalkCSVDataSet(
        filepath=_write(tmp_path, EXTRACT), lowercase_headers=False
    )
    frame = dataset.load()
    assert "BUTIK_ID" in frame.columns


def test_dayfirst_is_not_passed_to_read_csv(tmp_path):
    dataset = NordfalkCSVDataSet(
        filepath=_write(tmp_path, EXTRACT), load_args={"dayfirst": True}
    )
    frame = dataset.load()
    assert frame.attrs["dayfirst"] is True


def test_exists(tmp_path):
    path = _write(tmp_path, EXTRACT)
    assert NordfalkCSVDataSet(filepath=path).exists()
    assert not NordfalkCSVDataSet(filepath=str(tmp_path / "missing.csv")).exists()
