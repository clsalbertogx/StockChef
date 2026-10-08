from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    lead_time_days: int = Field(default=1, ge=1)
    minimum_order_value: Decimal = Field(default=Decimal("0"), ge=0)


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    lead_time_days: int
    status: str


class PurchaseSuggestion(BaseModel):
    ingredient_id: UUID
    name: str
    unit_symbol: str
    stock_total: str
    minimum_stock: str
    consumption_daily: str
    lead_time_days: int
    suggested_quantity: str
    reason: str
