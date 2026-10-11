from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LOSS_REASON = Literal[
    "expiration", "cooking_error", "damage", "theft", "return", "spoilage", "other"
]


class LossCreate(BaseModel):
    store_id: UUID | None = None
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)
    reason: LOSS_REASON
    occurred_at: datetime | None = None


class LossOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ingredient_id: UUID
    store_id: UUID
    quantity: Decimal
    cost: Decimal
    reason: str
    occurred_at: datetime


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ingredient_id: UUID
    type: str
    quantity: Decimal
    unit_cost: Decimal
    reason: str | None
    created_at: datetime


class CountItemIn(BaseModel):
    ingredient_id: UUID
    counted_quantity: Decimal = Field(ge=0)


class CountItemsIn(BaseModel):
    items: list[CountItemIn]


class InventoryCountItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ingredient_id: UUID
    system_quantity: Decimal
    counted_quantity: Decimal | None
    difference: Decimal | None
    adjusted: bool


class InventoryCountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    store_id: UUID
    status: str
    started_at: datetime
    closed_at: datetime | None
    items: list[InventoryCountItemOut] = []
