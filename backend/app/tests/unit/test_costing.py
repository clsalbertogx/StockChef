from decimal import Decimal

from app.modules.catalog.costing import ingredient_cost, recipe_cost


def test_xburger_queijo_cheddar() -> None:
    assert ingredient_cost(Decimal("0.030"), Decimal("45.00")) == Decimal("1.35")


def test_recipe_cost_sums_items() -> None:
    assert recipe_cost(
        [(Decimal("0.030"), Decimal("45.00")), (Decimal("2"), Decimal("1.00"))]
    ) == Decimal("3.35")
