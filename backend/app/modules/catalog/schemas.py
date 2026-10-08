from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


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
