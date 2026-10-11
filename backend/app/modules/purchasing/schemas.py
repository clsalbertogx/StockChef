from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupplierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    document: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    lead_time_days: int = Field(default=0, ge=0)
    minimum_order_value: Decimal = Field(default=Decimal("0"), ge=0)


class SupplierUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    document: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    lead_time_days: int | None = Field(None, ge=0)
    minimum_order_value: Decimal | None = Field(None, ge=0)
    active: bool | None = None


class SupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    lead_time_days: int
    active: bool = True


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


class PurchaseOrderItemIn(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: UUID
    expected_date: date | None = None
    items: list[PurchaseOrderItemIn] = Field(min_length=1)


class ReceiptItemIn(BaseModel):
    purchase_order_item_id: UUID
    received_quantity: Decimal = Field(gt=0)
    unit_cost: Decimal = Field(ge=0)


class GoodsReceiptIn(BaseModel):
    items: list[ReceiptItemIn] = Field(min_length=1)
    invoice_number: str | None = None
    notes: str | None = None


class PurchaseOrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ingredient_id: UUID
    quantity: Decimal
    unit_cost: Decimal
    received_quantity: Decimal


class PurchaseOrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    supplier_id: UUID
    status: str
    expected_date: date | None
    total_amount: Decimal
    approved_by: UUID | None
    created_at: datetime
    items: list[PurchaseOrderItemOut]

