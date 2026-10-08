from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class OrderItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    store_id: UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    items: list[OrderItemRequest] = Field(min_length=1)
    notes: str | None = None
    fulfillment_type: Literal["delivery", "pickup", "table"] = "delivery"
    channel: Literal["own_pwa", "whatsapp", "phone", "pos", "marketplace_future"] = "own_pwa"


class OrderItemOut(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class OrderOut(BaseModel):
    id: UUID
    code: str
    status: str
    customer_name: str | None
    customer_phone: str | None
    subtotal: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    order_items: list[OrderItemOut]
