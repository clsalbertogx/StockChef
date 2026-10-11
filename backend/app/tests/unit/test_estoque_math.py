from decimal import Decimal

from app.modules.inventory.service import weighted_average_cost


def test_primeira_entrada_usa_o_custo() -> None:
    assert weighted_average_cost(Decimal("0"), Decimal("0"),
                                 Decimal("10"), Decimal("10")) == Decimal("10.0000")


def test_entrada_ponderada() -> None:
    # 10 un a 10 + 10 un a 12 = média 11
    assert weighted_average_cost(Decimal("10"), Decimal("10"),
                                 Decimal("10"), Decimal("12")) == Decimal("11.0000")


def test_arredonda_4_casas() -> None:
    # 1 un a 1 + 2 un a 2 = 5/3 = 1.6667
    assert weighted_average_cost(Decimal("1"), Decimal("1"),
                                 Decimal("2"), Decimal("2")) == Decimal("1.6667")
