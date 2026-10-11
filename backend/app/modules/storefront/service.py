from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Category, Product, ProductModifier, Store
from app.modules.catalog.service import default_store
from app.modules.identity.models import Tenant
from app.modules.storefront.schemas import (
    ModifierOut,
    PublicCategoryOut,
    PublicMenuOut,
    PublicProductOut,
    PublicStoreOut,
    PublicTenantOut,
)


def _modifiers(db: Session, product_id: UUID) -> list[ModifierOut]:
    rows = db.scalars(
        select(ProductModifier)
        .where(ProductModifier.product_id == product_id, ProductModifier.active.is_(True))
        .order_by(ProductModifier.group_name, ProductModifier.modifier_name)
    ).all()
    return [
        ModifierOut(
            id=m.id, group_name=m.group_name, modifier_name=m.modifier_name,
            price_delta=m.price_delta, required=m.required,
            min_selection=m.min_selection, max_selection=m.max_selection,
        )
        for m in rows
    ]


def public_menu(
    db: Session, tenant: Tenant, store: Store, q: str | None, category_id: UUID | None
) -> PublicMenuOut:
    query = select(Product).where(Product.store_id == store.id, Product.active.is_(True))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    products = db.scalars(query.order_by(Product.name)).all()

    categories = db.scalars(
        select(Category)
        .where(Category.tenant_id == tenant.id, Category.active.is_(True))
        .order_by(Category.sort_order)
    ).all()

    return PublicMenuOut(
        tenant=PublicTenantOut(name=tenant.name, slug=tenant.slug),
        store=PublicStoreOut(
            id=store.id, name=store.name, delivery_enabled=store.delivery_enabled,
            pickup_enabled=store.pickup_enabled,
        ),
        categories=[
            PublicCategoryOut(id=c.id, name=c.name, sort_order=c.sort_order) for c in categories
        ],
        products=[
            PublicProductOut(
                id=p.id, name=p.name, description=p.description, price=p.price,
                image_url=p.image_url, category_id=p.category_id,
                preparation_time_minutes=p.preparation_time_minutes,
                modifiers=_modifiers(db, p.id),
            )
            for p in products
        ],
    )


def current_store(db: Session, tenant_id: UUID) -> Store:
    return default_store(db, tenant_id)
