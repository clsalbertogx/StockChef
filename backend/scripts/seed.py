#!/usr/bin/env python3
"""Seed idempotente: cria tenant demo com X-Burger, ficha, zona, pedido confirmado."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select

from app.core.db import SessionLocal, engine, Base
from app.modules.catalog.models import (
    Category,
    Ingredient,
    Product,
    ProductModifier,
    Recipe,
    RecipeItem,
    Store,
    Unit,
)
from app.modules.delivery.models import Zone
from app.modules.identity.models import Tenant, User
from app.modules.identity.security import hash_password
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem, Payment


DEMO_SLUG = "demo"
DEMO_EMAIL = "dono@demo.example"
DEMO_PASSWORD = "demo1234"
DEMO_TENANT_NAME = "Demo Restaurante"
DEMO_STORE_NAME = "Loja Principal"


def _unit(db, tenant_id: UUID, symbol: str, name: str, type_: str) -> Unit:
    u = db.scalar(
        select(Unit).where(Unit.tenant_id == tenant_id, Unit.symbol == symbol)
    )
    if u is None:
        u = Unit(tenant_id=tenant_id, name=name, symbol=symbol, type=type_)
        db.add(u)
        db.flush()
    return u


def _ingredient(db, tenant_id: UUID, unit_id: UUID, name: str, cost: str, min_stock: str = "5") -> Ingredient:
    ing = db.scalar(
        select(Ingredient).where(Ingredient.tenant_id == tenant_id, Ingredient.name == name)
    )
    if ing is None:
        ing = Ingredient(
            tenant_id=tenant_id,
            name=name,
            category="Insumo",
            base_unit_id=unit_id,
            average_cost=Decimal(cost),
            minimum_stock=Decimal(min_stock),
            status="active",
        )
        db.add(ing)
        db.flush()
    return ing


def main() -> None:
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Start transaction so after_begin event fires and sets app.tenant_id
        db.begin()

        # --- Tenant ---
        tenant = db.scalar(select(Tenant).where(Tenant.slug == DEMO_SLUG))
        if tenant is None:
            tenant = Tenant(name=DEMO_TENANT_NAME, slug=DEMO_SLUG, status="active")
            db.add(tenant)
            db.flush()
            print(f"[seed] Tenant criado: {tenant.name} ({tenant.slug})")
        else:
            print(f"[seed] Tenant já existe: {tenant.name}")

        from app.core.db import set_tenant
        set_tenant(db, tenant.id)

        # --- Store ---
        store = db.scalar(select(Store).where(Store.tenant_id == tenant.id, Store.status == "active"))
        if store is None:
            store = Store(tenant_id=tenant.id, name=DEMO_STORE_NAME, status="active")
            db.add(store)
            db.flush()
            print(f"[seed] Store criada: {store.name}")
        else:
            print(f"[seed] Store já existe: {store.name}")

        # --- Units ---
        un_kg = _unit(db, tenant.id, "kg", "Quilograma", "mass")
        un_g = _unit(db, tenant.id, "g", "Grama", "mass")
        un_un = _unit(db, tenant.id, "un", "Unidade", "count")
        un_ml = _unit(db, tenant.id, "ml", "Mililitro", "volume")
        un_l = _unit(db, tenant.id, "l", "Litro", "volume")

        # --- Ingredients ---
        pao = _ingredient(db, tenant.id, un_un.id, "Pão brioche", "1.50", "20")
        carne = _ingredient(db, tenant.id, un_kg.id, "Hambúrguer 150g", "8.00", "5")
        queijo = _ingredient(db, tenant.id, un_kg.id, "Queijo cheddar", "45.00", "2")
        alface = _ingredient(db, tenant.id, un_g.id, "Alface", "0.05", "100")
        tomate = _ingredient(db, tenant.id, un_kg.id, "Tomate", "6.00", "3")
        molho = _ingredient(db, tenant.id, un_kg.id, "Molho especial", "12.00", "1")

        # --- Category ---
        cat = db.scalar(select(Category).where(Category.tenant_id == tenant.id, Category.name == "Hambúrgueres"))
        if cat is None:
            cat = Category(tenant_id=tenant.id, name="Hambúrgueres", sort_order=1, active=True)
            db.add(cat)
            db.flush()

        # --- Product X-Burger ---
        product = db.scalar(select(Product).where(Product.store_id == store.id, Product.name == "X-Burger"))
        if product is None:
            product = Product(
                tenant_id=tenant.id,
                store_id=store.id,
                category_id=cat.id,
                name="X-Burger",
                description="Pão, carne 150g, queijo, alface, tomate, molho especial",
                price=Decimal("28.00"),
                image_url=None,
                active=True,
                preparation_time_minutes=12,
            )
            db.add(product)
            db.flush()
            print(f"[seed] Produto criado: {product.name}")

            # Recipe
            recipe = Recipe(tenant_id=tenant.id, product_id=product.id, status="active", version=1)
            db.add(recipe)
            db.flush()

            items = [
                (pao, Decimal("1"), un_un.id),
                (carne, Decimal("0.150"), un_kg.id),
                (queijo, Decimal("0.030"), un_kg.id),
                (alface, Decimal("15"), un_g.id),
                (tomate, Decimal("40"), un_g.id),
                (molho, Decimal("0.020"), un_kg.id),
            ]
            for ing, qty, u_id in items:
                db.add(RecipeItem(
                    tenant_id=tenant.id,
                    recipe_id=recipe.id,
                    ingredient_id=ing.id,
                    quantity=qty,
                    unit_id=u_id,
                ))

        else:
            print(f"[seed] Produto já existe: {product.name}")

        # --- Modifiers ---
        mod_group = "Ponto da carne"
        mods_data = [
            ("Mal passado", Decimal("0.00"), True, 1, 1),
            ("Ao ponto", Decimal("0.00"), False, 0, 1),
            ("Bem passado", Decimal("0.00"), False, 0, 1),
        ]
        for mod_name, price_delta, required, min_sel, max_sel in mods_data:
            exists = db.scalar(
                select(ProductModifier).where(
                    ProductModifier.product_id == product.id,
                    ProductModifier.group_name == mod_group,
                    ProductModifier.modifier_name == mod_name,
                )
            )
            if not exists:
                db.add(ProductModifier(
                    tenant_id=tenant.id,
                    product_id=product.id,
                    group_name=mod_group,
                    modifier_name=mod_name,
                    price_delta=price_delta,
                    required=required,
                    min_selection=min_sel,
                    max_selection=max_sel,
                    active=True,
                ))

        # Extras
        mod_group2 = "Extras"
        extras_data = [
            ("Bacon", Decimal("3.00"), False, 0, 2),
            ("Ovo", Decimal("2.00"), False, 0, 2),
            ("Cebola caramelizada", Decimal("1.50"), False, 0, 2),
        ]
        for mod_name, price_delta, required, min_sel, max_sel in extras_data:
            exists = db.scalar(
                select(ProductModifier).where(
                    ProductModifier.product_id == product.id,
                    ProductModifier.group_name == mod_group2,
                    ProductModifier.modifier_name == mod_name,
                )
            )
            if not exists:
                db.add(ProductModifier(
                    tenant_id=tenant.id,
                    product_id=product.id,
                    group_name=mod_group2,
                    modifier_name=mod_name,
                    price_delta=price_delta,
                    required=required,
                    min_selection=min_sel,
                    max_selection=max_sel,
                    active=True,
                ))

        # --- Zone ---
        zone = db.scalar(select(Zone).where(Zone.store_id == store.id, Zone.name == "Centro"))
        if zone is None:
            zone = Zone(
                tenant_id=tenant.id,
                store_id=store.id,
                name="Centro",
                cep_ranges=[{"start": "01000000", "end": "01999999"}],
                delivery_fee=Decimal("6.00"),
                min_order_value=Decimal("15.00"),
                eta_minutes=35,
                active=True,
            )
            db.add(zone)
            db.flush()
            print(f"[seed] Zona criada: {zone.name}")

        # --- Owner User ---
        user = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                name="Dono Demo",
                role="owner",
                status="active",
            )
            db.add(user)
            db.flush()
            print(f"[seed] Owner criado: {user.email}")

        # --- Demo Order (confirmed) ---
        demo_customer = db.scalar(
            select(Customer).where(Customer.tenant_id == tenant.id, Customer.phone == "11999999999")
        )
        if demo_customer is None:
            demo_customer = Customer(
                tenant_id=tenant.id,
                name="Cliente Demo",
                phone="11999999999",
                address={"street": "Rua Demo", "number": "123", "district": "Centro", "city": "SP", "state": "SP"},
            )
            db.add(demo_customer)
            db.flush()

        existing_order = db.scalar(
            select(Order).where(Order.tenant_id == tenant.id, Order.code.like("SC-DEMO%"))
        )
        if existing_order is None:
            from datetime import UTC, datetime, timedelta
            order = Order(
                tenant_id=tenant.id,
                store_id=store.id,
                customer_id=demo_customer.id,
                code="SC-DEMO001",
                status="confirmed",
                channel="own_pwa",
                fulfillment_type="delivery",
                subtotal=Decimal("28.00"),
                delivery_fee=Decimal("6.00"),
                total=Decimal("34.00"),
                notes="Pedido de demonstração",
                expected_time=datetime.now(UTC) + timedelta(minutes=47),
            )
            db.add(order)
            db.flush()

            db.add(OrderItem(
                tenant_id=tenant.id,
                order_id=order.id,
                product_id=product.id,
                quantity=1,
                unit_price=Decimal("28.00"),
                total_price=Decimal("28.00"),
                notes=None,
                modifiers=[],
                recipe_snapshot=[],
            ))

            db.add(OrderEvent(
                tenant_id=tenant.id,
                order_id=order.id,
                event_type="order.created",
                from_status=None,
                to_status="confirmed",
            ))
            db.add(OrderEvent(
                tenant_id=tenant.id,
                order_id=order.id,
                event_type="status.changed",
                from_status="received",
                to_status="confirmed",
            ))

            db.add(Payment(
                tenant_id=tenant.id,
                order_id=order.id,
                provider="cash",
                method="cash",
                amount=Decimal("34.00"),
                status="pending",
                idempotency_key=f"order.seed:{order.code}",
            ))
            print(f"[seed] Pedido demo criado: {order.code}")

        db.commit()
        print("\n✅ Seed concluído com sucesso!")
        print(f"   Login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        print(f"   Cardápio público: http://localhost:5173/cardapio/{DEMO_SLUG}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro no seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()