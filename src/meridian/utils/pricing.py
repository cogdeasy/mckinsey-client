"""Value normalisation for the Nordfalk extract.

The line value on the extract (omsaetning_dkk) is what the till rang up: net
of nothing. It carries 25% Danish VAT and, on drinks lines, the container
deposit ("pant") at 1.00, 1.50 or 3.00 DKK depending on the class. Both have
to come off before any price or elasticity work, in that order, because the
deposit is not VAT bearing in the client's till system.

Group reporting is in EUR at the frozen engagement rate.
"""
from meridian.utils.nordfalk_codes import DEPOSIT_CLASSES, FX_DKK_PER_EUR, VAT_RATE


def strip_deposit(gross_value, units, deposit_type):
    """Remove the container deposit from a gross line value."""
    rate = DEPOSIT_CLASSES.get(_clean(deposit_type), 0.0)
    units = max(units or 0, 0)
    return gross_value - (rate * units)


def strip_vat(value, vat_rate=VAT_RATE):
    return value / (1.0 + vat_rate)


def net_sales(gross_value, units, deposit_type, vat_rate=VAT_RATE):
    """Net (ex VAT, ex deposit) line value in DKK."""
    return strip_vat(strip_deposit(gross_value, units, deposit_type), vat_rate)


def unit_price(gross_value, units, deposit_type, vat_rate=VAT_RATE):
    if not units:
        return None
    return net_sales(gross_value, units, deposit_type, vat_rate) / units


def to_eur(value_dkk, rate=FX_DKK_PER_EUR):
    return value_dkk / rate


def discount_depth(normal_price, sales_price):
    """Fractional discount, 0 when the line is not on offer."""
    if not normal_price:
        return 0.0
    depth = (normal_price - sales_price) / normal_price
    if depth < 0:
        return 0.0
    return depth


def _clean(deposit_type):
    if deposit_type is None:
        return ""
    text = str(deposit_type).strip().upper()
    if text in ("NAN", "NONE"):
        return ""
    return text
