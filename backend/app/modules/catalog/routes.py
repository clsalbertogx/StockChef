from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.costing import ingredient_cost, margin, recipe_cost
from app.modules.catalog.models import (
    Ingredient,
    Product,
    Recipe,
    RecipeItem,
    StockLevel,
    Store,
    Unit,
)
from app.modules.catalog.schemas import (
    IngredientCreate,
    IngredientOut,
    IngredientPatch,
    ProductCreate,
    ProductOut,
    RecipeItemOut,
    RecipeOut,
    RecipeSetIn,
    UnitOut,
)
from app.modules.catalog.service import default_store, get_or_create_unit, stock_total, stock_totals

router = APIRouter(tags=["insumos"])


def _tenant_id(db: Session) -> UUID:
    """Tenant ativo da sessão — setado por get_tenant_db (app.core.deps)."""
    return db.info["tenant_id"]


def _require_store(db: Session, tid: UUID, store_id: UUID) -> UUID:
    """Valida que store_id pertence ao tenant ativo; senão 404 (evita escrita cross-tenant)."""
    store = db.get(Store, store_id)
    if store is None or store.tenant_id != UUID(str(tid)):
        raise DomainError("store_not_found", "Loja não encontrada.", status.HTTP_404_NOT_FOUND)
    return store.id


def _to_out(db: Session, ing: Ingredient, stock: Decimal | None = None) -> IngredientOut:
    unit = db.get(Unit, ing.base_unit_id)
    assert unit is not None
    if stock is None:
        stock = stock_total(db, ing.id)
    return IngredientOut(
        id=ing.id,
        name=ing.name,
        category=ing.category,
        base_unit=UnitOut(id=unit.id, symbol=unit.symbol),
        average_cost=ing.average_cost.quantize(Decimal("0.01")),
        minimum_stock=ing.minimum_stock.quantize(Decimal("0.0001")),
        status=ing.status,
        stock_total=stock.quantize(Decimal("0.01")),
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
    totals = stock_totals(db, [i.id for i in ings])
    return [_to_out(db, i, totals.get(i.id, Decimal("0"))) for i in ings]


@router.get("/insumos/{insumo_id}")
def get_insumo(insumo_id: UUID, db: Session = Depends(get_tenant_db)) -> IngredientOut:  # noqa: B008
    ing = db.get(Ingredient, insumo_id)
    if ing is None:
        raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
    return _to_out(db, ing)


@router.patch("/insumos/{insumo_id}")
def patch_insumo(
    insumo_id: UUID, payload: IngredientPatch, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> IngredientOut:
    ing = db.get(Ingredient, insumo_id)
    if ing is None:
        raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
    if payload.name is not None and payload.name != ing.name:
        taken = db.scalar(
            select(Ingredient).where(
                Ingredient.tenant_id == _tenant_id(db),
                Ingredient.name == payload.name,
                Ingredient.id != insumo_id,
            )
        )
        if taken is not None:
            raise DomainError(
                "insumo_exists", "Já existe um insumo com esse nome.", status.HTTP_409_CONFLICT
            )
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


@router.post("/produtos", status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_tenant_db)) -> ProductOut:  # noqa: B008
    tid = _tenant_id(db)
    store_id = (
        _require_store(db, tid, payload.store_id)
        if payload.store_id
        else default_store(db, tid).id
    )
    if db.scalar(
        select(Product).where(Product.store_id == store_id, Product.name == payload.name)
    ):
        raise DomainError(
            "product_exists",
            "Já existe um produto com esse nome na loja.",
            status.HTTP_409_CONFLICT,
        )
    product = Product(
        tenant_id=tid,
        store_id=store_id,
        name=payload.name,
        price=payload.price,
        description=payload.description,
        preparation_time_minutes=payload.preparation_time_minutes,
    )
    db.add(product)
    db.flush()
    db.add(Recipe(tenant_id=tid, product_id=product.id, version=1, status="draft"))
    db.commit()
    return ProductOut.model_validate(product)


@router.get("/produtos")
def list_produtos(db: Session = Depends(get_tenant_db)) -> list[ProductOut]:  # noqa: B008
    rows = db.scalars(
        select(Product).where(Product.tenant_id == _tenant_id(db)).order_by(Product.name)
    ).all()
    return [ProductOut.model_validate(p) for p in rows]


@router.get("/produtos/{product_id}")
def get_product(product_id: UUID, db: Session = Depends(get_tenant_db)) -> ProductOut:  # noqa: B008
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    return ProductOut.model_validate(product)


def _active_recipe_or_create(db: Session, tid: UUID, product_id: UUID) -> Recipe:
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.product_id == product_id, Recipe.status == "active")
        .order_by(Recipe.version.desc())
        .limit(1)
    )
    if recipe is None:
        draft = db.scalar(
            select(Recipe)
            .where(Recipe.product_id == product_id, Recipe.status == "draft")
            .order_by(Recipe.version.desc())
            .limit(1)
        )
        if draft is not None:
            draft.status = "active"
            recipe = draft
        else:
            maxv = (
                db.scalar(select(func.max(Recipe.version)).where(Recipe.product_id == product_id))
                or 0
            )
            recipe = Recipe(tenant_id=tid, product_id=product_id, version=maxv + 1, status="active")
            db.add(recipe)
            db.flush()
    return recipe


@router.post("/produtos/{product_id}/ficha-tecnica")
def set_ficha(
    product_id: UUID, payload: RecipeSetIn, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> RecipeOut:
    tid = _tenant_id(db)
    if db.get(Product, product_id) is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    recipe = _active_recipe_or_create(db, tid, product_id)
    db.execute(delete(RecipeItem).where(RecipeItem.recipe_id == recipe.id))
    items: list[RecipeItem] = []
    for it in payload.items:
        ing = db.get(Ingredient, it.ingredient_id)
        if ing is None:
            raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
        items.append(
            RecipeItem(
                tenant_id=tid,
                recipe_id=recipe.id,
                ingredient_id=ing.id,
                quantity=it.quantity,
                unit_id=ing.base_unit_id,
            )
        )
    db.add_all(items)
    db.flush()
    db.commit()
    return _build_recipe_out(db, recipe)


@router.get("/produtos/{product_id}/ficha-tecnica")
def get_ficha(product_id: UUID, db: Session = Depends(get_tenant_db)) -> RecipeOut:  # noqa: B008
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.product_id == product_id)
        .order_by(Recipe.version.desc())
        .limit(1)
    )
    if recipe is None:
        raise DomainError("not_found", "Produto sem ficha técnica.", status.HTTP_404_NOT_FOUND)
    return _build_recipe_out(db, recipe)


def _build_recipe_out(db: Session, recipe: Recipe) -> RecipeOut:
    items = db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all()
    out_items: list[RecipeItemOut] = []
    pairs: list[tuple[Decimal, Decimal]] = []
    for it in items:
        ing = db.get(Ingredient, it.ingredient_id)
        unit = db.get(Unit, it.unit_id)
        assert ing is not None  # FK de recipe_items garante existência
        assert unit is not None
        out_items.append(
            RecipeItemOut(
                ingredient_id=it.ingredient_id,
                name=ing.name,
                unit_symbol=unit.symbol,
                quantity=it.quantity.quantize(Decimal("0.0001")),
                cost=ingredient_cost(it.quantity, ing.average_cost),
            )
        )
        pairs.append((it.quantity, ing.average_cost))
    return RecipeOut(
        product_id=recipe.product_id,
        status=recipe.status,
        version=recipe.version,
        items=out_items,
        total_cost=recipe_cost(pairs),
    )


@router.get("/produtos/{product_id}/margem")
def get_margin(product_id: UUID, db: Session = Depends(get_tenant_db)) -> dict:  # noqa: B008
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    recipe = db.scalar(
        select(Recipe)
        .where(Recipe.product_id == product_id, Recipe.status == "active")
        .order_by(Recipe.version.desc())
        .limit(1)
    )
    cost = Decimal("0.00")
    if recipe is not None:
        items = db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all()
        pairs: list[tuple[Decimal, Decimal]] = []
        for it in items:
            ing = db.get(Ingredient, it.ingredient_id)
            assert ing is not None  # FK de recipe_items garante existência
            pairs.append((it.quantity, ing.average_cost))
        cost = recipe_cost(pairs)
    value, percent = margin(product.price, cost)
    return {
        "product_id": str(product_id),
        "name": product.name,
        "price": str(product.price),
        "cost": str(cost),
        "margin_value": str(value),
        "margin_percent": None if percent is None else str(percent),
    }
