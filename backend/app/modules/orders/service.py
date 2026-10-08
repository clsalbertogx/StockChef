from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import Recipe, RecipeItem, StockLevel

MISSING_HTTP = 422


def load_active_recipe(db: Session, product_id: UUID) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.product_id == product_id, Recipe.status == "active")
        .order_by(Recipe.version.desc())
        .limit(1)
    )
    if recipe is None:
        raise DomainError(
            "recipe_missing", "Produto sem ficha técnica ativa.", MISSING_HTTP
        )
    return recipe


def availability(
    db: Session, store_id: UUID, items: list[tuple[UUID, int]]
) -> None:
    """Eleva 422 se algum insumo ficar aquém do exigido."""
    required: defaultdict[UUID, Decimal] = defaultdict(Decimal)
    for product_id, qty in items:
        recipe = load_active_recipe(db, product_id)
        for it in db.scalars(
            select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)
        ).all():
            required[it.ingredient_id] += it.quantity * qty

    missing = []
    for ingredient_id, need in required.items():
        have = (
            db.scalar(
                select(StockLevel.quantity).where(
                    StockLevel.store_id == store_id,
                    StockLevel.ingredient_id == ingredient_id,
                )
            )
            or Decimal("0")
        )
        if need > have:
            missing.append(
                {
                    "ingredient_id": str(ingredient_id),
                    "required": str(need),
                    "available": str(have),
                }
            )
    if missing:
        raise DomainError(
            "insufficient_stock",
            "Estoque insuficiente para o pedido.",
            MISSING_HTTP,
            extra={"missing": missing},
        )


def availability_ok(db: Session, store_id: UUID, items: list[tuple[UUID, int]]) -> bool:
    try:
        availability(db, store_id, items)
        return True
    except DomainError as exc:
        if exc.code == "insufficient_stock":
            return False
        raise


def recipe_snapshot(db: Session, product_id: UUID) -> list[dict]:
    recipe = load_active_recipe(db, product_id)
    return [
        {
            "ingredient_id": str(it.ingredient_id),
            "quantity": str(it.quantity),
            "unit_id": str(it.unit_id),
        }
        for it in db.scalars(
            select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)
        ).all()
    ]
