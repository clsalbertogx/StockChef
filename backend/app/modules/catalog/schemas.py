from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UnitOut(BaseModel):
    id: UUID
    symbol: str


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = None
    base_unit_symbol: str = Field(min_length=1, max_length=20)
    average_cost: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)
    initial_stock: Decimal = Field(default=Decimal("0"), ge=0)


class IngredientPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    average_cost: Decimal | None = Field(default=None, ge=0)
    minimum_stock: Decimal | None = Field(default=None, ge=0)


class IngredientOut(BaseModel):
    id: UUID
    name: str
    category: str | None
    base_unit: UnitOut
    average_cost: Decimal
    minimum_stock: Decimal
    status: str
    stock_total: Decimal


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0)
    store_id: UUID | None = None
    description: str | None = None
    preparation_time_minutes: int = Field(default=10, ge=0)


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    price: Decimal
    active: bool
    preparation_time_minutes: int


class RecipeItemIn(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)


class RecipeSetIn(BaseModel):
    items: list[RecipeItemIn] = Field(min_length=1)


class RecipeItemOut(BaseModel):
    ingredient_id: UUID
    name: str
    unit_symbol: str
    quantity: Decimal
    cost: Decimal


class RecipeOut(BaseModel):
    product_id: UUID
    status: str
    version: int
    items: list[RecipeItemOut]
    total_cost: Decimal
