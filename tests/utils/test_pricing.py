import pytest

from meridian.utils import pricing


def test_deposit_comes_off_before_vat():
    # 100 units of a class C line at 15.00 DKK gross incl. 3.00 deposit.
    gross = 1500.0
    net = pricing.net_sales(gross, 100, "C")
    assert net == pytest.approx((1500.0 - 300.0) / 1.25)


def test_deposit_is_ignored_on_return_lines():
    assert pricing.strip_deposit(-150.0, -10, "C") == -150.0


def test_unknown_or_blank_deposit_class_is_zero():
    assert pricing.strip_deposit(100.0, 10, "") == 100.0
    assert pricing.strip_deposit(100.0, 10, "nan") == 100.0
    assert pricing.strip_deposit(100.0, 10, None) == 100.0
    assert pricing.strip_deposit(100.0, 10, "D") == 100.0


def test_deposit_classes_are_the_client_values():
    assert pricing.strip_deposit(100.0, 10, "A") == 90.0
    assert pricing.strip_deposit(100.0, 10, "B") == 85.0
    assert pricing.strip_deposit(100.0, 10, "c") == 70.0


def test_unit_price_is_net_of_vat_and_deposit():
    price = pricing.unit_price(1500.0, 100, "C")
    assert price == pytest.approx(9.6)


def test_unit_price_is_none_without_units():
    assert pricing.unit_price(1500.0, 0, "C") is None


def test_to_eur_uses_the_frozen_engagement_rate():
    assert pricing.to_eur(7443.6) == pytest.approx(1000.0, rel=1e-4)


@pytest.mark.parametrize(
    "normal,sales,expected",
    [
        (10.0, 7.5, 0.25),
        (10.0, 10.0, 0.0),
        (10.0, 12.0, 0.0),
        (0.0, 5.0, 0.0),
        (None, 5.0, 0.0),
    ],
)
def test_discount_depth(normal, sales, expected):
    assert pricing.discount_depth(normal, sales) == pytest.approx(expected)
