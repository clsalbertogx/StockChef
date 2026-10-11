from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


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
