from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Ingredient, StockMovement, Supplier, Unit
from app.modules.catalog.service import stock_totals

# PONTAIL: Fator de segurança de 20% sobre estoque mínimo
SAFETY_FACTOR = Decimal("0.2")


def suggested_qty(
    *,
    current: Decimal,
    minimum: Decimal,
    lead_days: Decimal,
    daily: Decimal,
    max_stock: Decimal | None,
) -> Decimal:
    safety = minimum * SAFETY_FACTOR
    suggested = minimum + lead_days * daily + safety - current
    if max_stock is not None:
        suggested = min(suggested, max_stock - current)
    return max(Decimal("0"), suggested).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def purchase_suggestion(
    db: Session, tenant_id: UUID | str, store_id: UUID, days: int = 14
) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=days)
    sales = dict(
        db.execute(
            select(StockMovement.ingredient_id, func.sum(StockMovement.quantity))
            .where(
                StockMovement.tenant_id == str(tenant_id),
                StockMovement.store_id == store_id,
                StockMovement.type == "sale",
                StockMovement.created_at >= since,
            )
            .group_by(StockMovement.ingredient_id)
        ).all()
    )

    ings = db.scalars(
        select(Ingredient).where(
            Ingredient.tenant_id == str(tenant_id), Ingredient.status == "active"
        )
    ).all()
    totals = stock_totals(db, [i.id for i in ings])
    units = {
        u.id: u.symbol
        for u in db.scalars(select(Unit).where(Unit.tenant_id == str(tenant_id))).all()
    }

    result: list[dict] = []
    for ing in ings:
        current = totals.get(ing.id, Decimal("0"))
        sold = sales.get(ing.id, Decimal("0"))
        daily = max(Decimal("0"), -sold / Decimal(days))
        lead = Decimal("1")
        if ing.default_supplier_id:
            sup = db.get(Supplier, ing.default_supplier_id)
            if sup is not None:
                lead = Decimal(sup.lead_time_days)
        qty = suggested_qty(
            current=current,
            minimum=ing.minimum_stock,
            lead_days=lead,
            daily=daily,
            max_stock=ing.maximum_stock,
        )
        if qty <= 0:
            continue
        reason = (
            f"Consumo {daily:.2f}/dia + lead time {lead}d + mínimo "
            f"{ing.minimum_stock}: sugerido {qty}"
        )
        result.append(
            {
                "ingredient_id": str(ing.id),
                "name": ing.name,
                "unit_symbol": units.get(ing.base_unit_id, ""),
                "stock_total": str(current),
                "minimum_stock": str(ing.minimum_stock),
                "consumption_daily": str(daily),
                "lead_time_days": int(lead),
                "suggested_quantity": str(qty),
                "reason": reason,
            }
        )
    return result
