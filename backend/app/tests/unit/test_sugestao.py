from decimal import Decimal

from app.modules.purchasing.service import suggested_qty


def test_formula_base() -> None:
    # mínimo 5, lead 1, consumo 0.5/dia, segurança 1 (5*0.2), estoque 3 → 5+0.5+1-3 = 3.5
    assert suggested_qty(
        current=Decimal("3"), minimum=Decimal("5"), lead_days=Decimal("1"),
        daily=Decimal("0.5"), max_stock=None,
    ) == Decimal("3.5000")

def test_respeita_maximo() -> None:
    # teto: máximo 6 → 6-3 = 3
    assert suggested_qty(
        current=Decimal("3"), minimum=Decimal("5"), lead_days=Decimal("1"),
        daily=Decimal("0.5"), max_stock=Decimal("6"),
    ) == Decimal("3.0000")

def test_nunca_negativo() -> None:
    assert suggested_qty(
        current=Decimal("50"), minimum=Decimal("5"), lead_days=Decimal("1"),
        daily=Decimal("0.5"), max_stock=None,
    ) == Decimal("0.0000")
