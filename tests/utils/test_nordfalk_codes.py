import pytest

from meridian.utils import nordfalk_codes as codes


@pytest.mark.parametrize(
    "store_id,expected",
    [
        ("1101", True),
        ("4201", True),
        (1101, True),
        (" 1101 ", True),
        ("110", False),
        ("11011", False),
        ("11A1", False),
        (None, False),
    ],
)
def test_is_valid_store_id(store_id, expected):
    assert codes.is_valid_store_id(store_id) is expected


def test_depots_and_test_stores():
    assert codes.is_depot("9001")
    assert not codes.is_depot("1101")
    assert codes.is_test_store("1199")
    assert not codes.is_test_store("1101")


def test_region_of_uses_first_two_characters():
    assert codes.region_of("1101") == "11"
    assert codes.region_of("6201") == "62"
    assert codes.region_of("110") is None


def test_region_names_and_groups():
    assert codes.region_name("11") == "Hovedstaden"
    assert codes.region_name("13") == "Ukendt"
    assert codes.region_group("11") == "STORBY"
    assert codes.region_group("62") == "JYLLAND"
    assert codes.region_group("99") == "OEVRIGE"


def test_category_of_handles_the_2019_migration_overrides():
    assert codes.category_of("1004") == "10"
    assert codes.category_of("1219") == "12"
    assert codes.category_of("2013") == "20"


def test_fresh_categories():
    assert codes.is_fresh("10")
    assert codes.is_fresh("12")
    assert not codes.is_fresh("30")


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("10023", "10023"),
        (10023, "10023"),
        ("10023.0", "10023"),
        (" 923 ", "00923"),
    ],
)
def test_normalise_sku(raw, expected):
    assert codes.normalise_sku(raw) == expected


def test_promo_weight_falls_back_for_unknown_mechanics():
    assert codes.promo_weight("AVIS") == 1.0
    assert codes.promo_weight("kupon") == 0.35
    assert codes.promo_weight("XX") == 0.25
    assert codes.promo_weight("") == 0.0
    assert codes.promo_weight(None) == 0.0
