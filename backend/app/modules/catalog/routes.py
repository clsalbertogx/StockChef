from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.models import Ingredient, StockLevel
from app.modules.catalog.schemas import IngredientCreate, IngredientOut, IngredientPatch, UnitOut
from app.modules.catalog.service import default_store, get_or_create_unit, stock_total

router = APIRouter(tags=["insumos"])


def _tenant_id(db: Session) -> UUID:
    """Tenant ativo da sessão — setado por get_tenant_db (app.core.deps)."""
    return db.info["tenant_id"]


def _to_out(db: Session, ing: Ingredient) -> IngredientOut:
    from app.modules.catalog.models import Unit

    unit = db.get(Unit, ing.base_unit_id)
    assert unit is not None
    return IngredientOut(
        id=ing.id,
        name=ing.name,
        category=ing.category,
        base_unit=UnitOut(id=unit.id, symbol=unit.symbol),
        average_cost=ing.average_cost,
        minimum_stock=ing.minimum_stock,
        status=ing.status,
        stock_total=stock_total(db, ing.id).quantize(Decimal("0.01")),
    )


@router.post("/insumos", status_code=status.HTTP_201_CREATED)
def create_insumo(
    payload: IngredientCreate, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> IngredientOut:
    if db.scalar(
        select(Ingredient).where(
            Ingredient.tenant_id == _tenant_id(db), Ingredient.name == payload.name
        )
    ):
        raise DomainError(
            "insumo_exists", "Já existe um insumo com esse nome.", status.HTTP_409_CONFLICT
        )
    unit = get_or_create_unit(db, _tenant_id(db), payload.base_unit_symbol)
    ing = Ingredient(
        tenant_id=_tenant_id(db),
        name=payload.name,
        category=payload.category,
        base_unit_id=unit.id,
        average_cost=payload.average_cost,
        minimum_stock=payload.minimum_stock,
        status="active",
    )
    db.add(ing)
    db.flush()
    if payload.initial_stock > 0:
        store = default_store(db, _tenant_id(db))
        db.add(
            StockLevel(
                tenant_id=_tenant_id(db),
                store_id=store.id,
                ingredient_id=ing.id,
                quantity=payload.initial_stock,
                average_cost=payload.average_cost,
            )
        )
    db.commit()
    return _to_out(db, ing)


@router.get("/insumos")
def list_insumos(db: Session = Depends(get_tenant_db)) -> list[IngredientOut]:  # noqa: B008
    ings = db.scalars(
        select(Ingredient)
        .where(Ingredient.tenant_id == _tenant_id(db), Ingredient.status != "archived")
        .order_by(Ingredient.name)
    ).all()
    return [_to_out(db, i) for i in ings]


@router.patch("/insumos/{insumo_id}")
def patch_insumo(
    insumo_id: UUID, payload: IngredientPatch, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> IngredientOut:
    ing = db.get(Ingredient, insumo_id)
    if ing is None:
        raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
    for field in ("name", "category", "minimum_stock"):
        value = getattr(payload, field)
        if value is not None:
            setattr(ing, field, value)
    if payload.average_cost is not None:
        ing.average_cost = payload.average_cost
        db.execute(
            update(StockLevel)
            .where(StockLevel.ingredient_id == insumo_id)
            .values(average_cost=payload.average_cost)
        )
    db.commit()
    return _to_out(db, ing)
