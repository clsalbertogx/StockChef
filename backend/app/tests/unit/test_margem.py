from decimal import Decimal

from app.modules.catalog.costing import margin


def test_price_minus_cost() -> None:
    value, percent = margin(Decimal("20.00"), Decimal("3.35"))
    assert value == Decimal("16.65")
    assert percent == Decimal("83.25")


def test_percent_none_when_price_zero() -> None:
    value, percent = margin(Decimal("0"), Decimal("3.35"))
    assert value == Decimal("-3.35")
    assert percent is None
