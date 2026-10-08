from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def ingredient_cost(quantity: Decimal, average_cost: Decimal) -> Decimal:
    return (quantity * average_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recipe_cost(quantities_costs: list[tuple[Decimal, Decimal]]) -> Decimal:
    total = sum((ingredient_cost(q, c) for q, c in quantities_costs), Decimal("0"))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
