"""Seed de demonstração do StockChef.

Uso: cd backend && ../.venv/bin/python scripts/seed.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal, set_tenant
from app.modules.catalog.models import (
    Ingredient,
    Product,
    Recipe,
    RecipeItem,
    StockLevel,
    Store,
    Unit,
)
from app.modules.catalog.service import default_store
from app.modules.identity.models import Tenant, User
from app.modules.identity.security import hash_password
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.outbox import drain_outbox
from app.modules.orders.routes import confirm_order

EMAIL = "dono@demo.example"
PASSWORD = "demo1234"
SLUG = "demo"


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Tenant).where(Tenant.slug == SLUG)):
            print("Tenant 'demo' já existe — nada a fazer.")
            return

        _create_demo(db)
        print("Seed concluído:")
        print(f"  login: {EMAIL} / {PASSWORD}")
        print(f"  tenant: {SLUG} · X-Burger custo 9.85 · margem 50.75%")
    except Exception as exc:
        # Idempotência sob falha parcial: remove o tenant criado pela metade para
        # que a próxima execução recomece do zero (senão re-rodar diria "nada a fazer").
        db.rollback()
        db.execute(delete(Tenant).where(Tenant.slug == SLUG))
        db.commit()
        print(f"Seed falhou (rollback do tenant '{SLUG}'): {exc}")
        raise
    finally:
        db.close()


def _create_demo(db: Session) -> None:
    tenant = Tenant(name="Lanches Demo", slug=SLUG, status="active")
    db.add(tenant)
    db.flush()
    set_tenant(db, tenant.id)

    db.add(Store(tenant_id=tenant.id, name="Loja principal", status="active"))
    for symbol, name, typ in (
        ("kg", "Quilograma", "mass"),
        ("g", "Grama", "mass"),
        ("ml", "Mililitro", "volume"),
        ("l", "Litro", "volume"),
        ("un", "Unidade", "count"),
    ):
        db.add(Unit(tenant_id=tenant.id, name=name, symbol=symbol, type=typ))
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=EMAIL,
        password_hash=hash_password(PASSWORD),
        name="Dona Demo",
        role="owner",
        status="active",
    )
    db.add(user)
    db.flush()

    store = default_store(db, tenant.id)
    kg = db.scalar(select(Unit).where(Unit.tenant_id == tenant.id, Unit.symbol == "kg"))
    un = db.scalar(select(Unit).where(Unit.tenant_id == tenant.id, Unit.symbol == "un"))
    assert kg is not None
    assert un is not None

    specs = [
        ("Queijo cheddar", kg.id, Decimal("45.00"), Decimal("3.000")),
        ("Pão brioche", un.id, Decimal("2.00"), Decimal("50")),
        ("Carne 160g", kg.id, Decimal("30.00"), Decimal("5.000")),
    ]
    ingredients: dict[str, Ingredient] = {}
    for name, unit_id, cost, stock_qty in specs:
        ing = Ingredient(
            tenant_id=tenant.id,
            name=name,
            base_unit_id=unit_id,
            average_cost=cost,
            status="active",
        )
        db.add(ing)
        db.flush()
        db.add(
            StockLevel(
                tenant_id=tenant.id,
                store_id=store.id,
                ingredient_id=ing.id,
                quantity=stock_qty,
                average_cost=cost,
            )
        )
        ingredients[name] = ing

    FICHA = (("Queijo cheddar", "0.030"), ("Pão brioche", "2"), ("Carne 160g", "0.150"))

    product = Product(
        tenant_id=tenant.id,
        store_id=store.id,
        name="X-Burger",
        price=Decimal("20.00"),
        preparation_time_minutes=15,
    )
    db.add(product)
    db.flush()
    recipe = Recipe(tenant_id=tenant.id, product_id=product.id, version=1, status="active")
    db.add(recipe)
    db.flush()
    for name, qty in FICHA:
        db.add(
            RecipeItem(
                tenant_id=tenant.id,
                recipe_id=recipe.id,
                ingredient_id=ingredients[name].id,
                quantity=Decimal(qty),
                unit_id=ingredients[name].base_unit_id,
            )
        )
    db.flush()

    order_config = {
        "tenant_id": tenant.id,
        "store_id": store.id,
        "code": "SC-DEMO-1",
        "status": "received",
        "subtotal": Decimal("20.00"),
        "total": Decimal("20.00"),
    }
    order = Order(**order_config)
    db.add(order)
    db.flush()
    recipe_snapshot = [
        {
            "ingredient_id": str(ingredients[n].id),
            "quantity": q,
            "unit_id": str(ingredients[n].base_unit_id),
        }
        for n, q in FICHA
    ]
    db.add(
        OrderItem(
            tenant_id=tenant.id,
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=Decimal("20.00"),
            total_price=Decimal("20.00"),
            recipe_snapshot=recipe_snapshot,
        )
    )
    db.commit()

    confirm_order(order_id=order.id, background_tasks=BackgroundTasks(), db=db)
    drain_outbox(tenant.id)
    db.commit()


if __name__ == "__main__":
    seed()