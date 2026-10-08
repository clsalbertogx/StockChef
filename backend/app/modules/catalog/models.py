from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(UTC)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    address: Mapped[dict] = mapped_column(JSONB, default=dict)
    phone: Mapped[str | None] = mapped_column(String, default=None)
    email: Mapped[str | None] = mapped_column(String, default=None)
    opening_hours: Mapped[dict] = mapped_column(JSONB, default=dict)
    delivery_enabled: Mapped[bool] = mapped_column(default=True)
    pickup_enabled: Mapped[bool] = mapped_column(default=True)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Unit(Base):
    __tablename__ = "units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "symbol", name="units_tenant_id_symbol_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="count")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID | None] = mapped_column(ForeignKey("stores.id"), default=None)
    name: Mapped[str] = mapped_column(String)
    sort_order: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    document: Mapped[str | None] = mapped_column(String, default=None)
    contact_name: Mapped[str | None] = mapped_column(String, default=None)
    email: Mapped[str | None] = mapped_column(String, default=None)
    phone: Mapped[str | None] = mapped_column(String, default=None)
    lead_time_days: Mapped[int] = mapped_column(default=1)
    minimum_order_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Ingredient(Base):
    __tablename__ = "ingredients"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="ingredients_tenant_id_name_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, default=None)
    base_unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    default_supplier_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("suppliers.id"), default=None
    )
    average_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    maximum_stock: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    shelf_life_days: Mapped[int | None] = mapped_column(default=None)
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StockLevel(Base):
    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint(
            "store_id", "ingredient_id", name="stock_levels_store_id_ingredient_id_key"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    average_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    reference_type: Mapped[str | None] = mapped_column(String, default=None)
    reference_id: Mapped[UUID | None] = mapped_column(default=None)
    reason: Mapped[str | None] = mapped_column(String, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, default=None)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("store_id", "name", name="products_store_id_name_key"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), default=None)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String, default=None)
    active: Mapped[bool] = mapped_column(default=True)
    stock_control_enabled: Mapped[bool] = mapped_column(default=True)
    preparation_time_minutes: Mapped[int] = mapped_column(default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint("product_id", "version", name="recipes_product_id_version_key"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String, default="draft")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    optional: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
