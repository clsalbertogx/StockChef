from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


def _norm(cep: str) -> str:
    return re.sub(r"\D", "", cep)


class CepRangeValidationError(ValueError):
    pass


class CepRange(BaseModel):
    start: str
    end: str

    @model_validator(mode="after")
    def validate_ranges(self) -> CepRange:
        s = _norm(self.start)
        e = _norm(self.end)
        if len(s) != 8 or len(e) != 8:
            raise CepRangeValidationError("CEP deve ter 8 dígitos")
        if s > e:
            raise CepRangeValidationError("start não pode ser maior que end")
        self.start = s
        self.end = e
        return self


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    store_id: UUID | None = None
    cep_ranges: list[CepRange] = []
    delivery_fee: Decimal = Field(default=Decimal("0"), ge=0)
    min_order_value: Decimal = Field(default=Decimal("0"), ge=0)
    eta_minutes: int = Field(default=30, ge=0)


class ZonePatch(BaseModel):
    name: str | None = None
    cep_ranges: list[CepRange] | None = None
    delivery_fee: Decimal | None = Field(default=None, ge=0)
    min_order_value: Decimal | None = Field(default=None, ge=0)
    eta_minutes: int | None = Field(default=None, ge=0)
    active: bool | None = None


class ZoneOut(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    cep_ranges: list
    delivery_fee: Decimal
    min_order_value: Decimal
    eta_minutes: int
    active: bool


# ===== Driver Schemas =====


class DriverCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str = Field(min_length=10, max_length=20)
    document: str | None = Field(default=None, max_length=20)
    vehicle_type: Literal["motorcycle", "bicycle", "car", "van", "other"] = "motorcycle"
    plate: str | None = Field(default=None, max_length=10)
    payment_model: Literal[
        "per_delivery", "hourly", "monthly", "fixed_route"
    ] = "per_delivery"


class DriverPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, min_length=10, max_length=20)
    document: str | None = Field(default=None, max_length=20)
    vehicle_type: Literal["motorcycle", "bicycle", "car", "van", "other"] | None = None
    plate: str | None = Field(default=None, max_length=10)
    payment_model: Literal[
        "per_delivery", "hourly", "monthly", "fixed_route"
    ] | None = None
    status: Literal["active", "inactive", "suspended"] | None = None


class DriverOut(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    phone: str
    document: str | None
    vehicle_type: str
    plate: str | None
    payment_model: str
    status: str
    rating_average: Decimal
    created_at: datetime
    updated_at: datetime


# ===== Delivery Schemas =====


class DeliveryCreate(BaseModel):
    order_id: UUID
    driver_id: UUID | None = None
    eta_minutes: int | None = Field(default=None, ge=0)
    route_hint: dict = Field(default_factory=dict)


class DeliveryPatch(BaseModel):
    driver_id: UUID | None = None
    eta_minutes: int | None = Field(default=None, ge=0)
    route_hint: dict | None = None
    occurrence: str | None = None


class DeliveryOut(BaseModel):
    id: UUID
    tenant_id: UUID
    order_id: UUID
    driver_id: UUID | None
    status: str
    assigned_at: datetime | None
    picked_up_at: datetime | None
    delivered_at: datetime | None
    eta_minutes: int | None
    route_hint: dict
    occurrence: str | None
    created_at: datetime
    updated_at: datetime


class DeliveryAssign(BaseModel):
    driver_id: UUID


class DeliveryStatusUpdate(BaseModel):
    status: Literal[
        "pending",
        "assigned",
        "picked_up",
        "in_transit",
        "delivered",
        "failed",
        "canceled",
    ]
    occurrence: str | None = None


# ===== Proof of Delivery Schemas =====


class ProofOfDeliveryCreate(BaseModel):
    type: Literal["photo", "signature", "pin", "customer_confirmation"]
    file_url: str | None = None
    received_by: str | None = None


class ProofOfDeliveryOut(BaseModel):
    id: UUID
    tenant_id: UUID
    delivery_id: UUID
    type: str
    file_url: str | None
    received_by: str | None
    created_at: datetime