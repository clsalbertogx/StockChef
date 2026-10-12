from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ModifierOut(BaseModel):
    id: UUID
    group_name: str
    modifier_name: str
    price_delta: Decimal
    required: bool
    min_selection: int
    max_selection: int | None


class PublicProductOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: Decimal
    image_url: str | None
    category_id: UUID | None
    preparation_time_minutes: int
    modifiers: list[ModifierOut]


class PublicCategoryOut(BaseModel):
    id: UUID
    name: str
    sort_order: int


class PublicStoreOut(BaseModel):
    id: UUID
    name: str
    delivery_enabled: bool
    pickup_enabled: bool


class PublicTenantOut(BaseModel):
    name: str
    slug: str


class PublicMenuOut(BaseModel):
    tenant: PublicTenantOut
    store: PublicStoreOut
    categories: list[PublicCategoryOut]
    products: list[PublicProductOut]


class DeliveryEstimateOut(BaseModel):
    covered: bool
    zone_name: str | None
    delivery_fee: Decimal
    min_order_value: Decimal
    eta_minutes: int


class PublicOrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)
    notes: str | None = None
    modifier_ids: list[UUID] = []


class PublicOrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(min_length=8, max_length=20)
    fulfillment_type: Literal["delivery", "pickup"] = "delivery"
    cep: str | None = None
    address: dict | None = None
    notes: str | None = None
    scheduled_time: datetime | None = None
    idempotency_key: str = Field(min_length=8, max_length=64)
    items: list[PublicOrderItemIn] = Field(min_length=1)


class PublicOrderItemOut(BaseModel):
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    modifiers: list


class PublicOrderOut(BaseModel):
    code: str
    status: str
    fulfillment_type: str
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    eta_minutes: int | None
    created_at: datetime
    items: list[PublicOrderItemOut]


class PublicOrderConfirm(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=64)
