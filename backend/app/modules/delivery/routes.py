from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.service import default_store
from app.modules.delivery.models import Zone
from app.modules.delivery.schemas import CepRange, ZoneCreate, ZoneOut, ZonePatch

router = APIRouter(tags=["entregas"])


def _tenant_id(db: Session) -> UUID:
    return db.info["tenant_id"]


def _to_out(z: Zone) -> ZoneOut:
    return ZoneOut(
        id=z.id, store_id=z.store_id, name=z.name, cep_ranges=z.cep_ranges or [],
        delivery_fee=z.delivery_fee, min_order_value=z.min_order_value,
        eta_minutes=z.eta_minutes, active=z.active,
    )


def _ranges(payload_ranges: list[CepRange]) -> list[dict]:
    return [{"start": r.start, "end": r.end} for r in payload_ranges]


@router.post("/zonas", status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreate,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ZoneOut:
    tid = _tenant_id(db)
    store_id = payload.store_id or default_store(db, tid).id
    zone = Zone(
        tenant_id=tid, store_id=store_id, name=payload.name,
        cep_ranges=_ranges(payload.cep_ranges), delivery_fee=payload.delivery_fee,
        min_order_value=payload.min_order_value, eta_minutes=payload.eta_minutes,
    )
    db.add(zone)
    db.commit()
    return _to_out(zone)


@router.get("/zonas")
def list_zones(db: Session = Depends(get_tenant_db)) -> list[ZoneOut]:  # noqa: B008
    rows = db.scalars(
        select(Zone).where(Zone.tenant_id == _tenant_id(db)).order_by(Zone.name)
    ).all()
    return [_to_out(z) for z in rows]


@router.patch("/zonas/{zone_id}")
def patch_zone(
    zone_id: UUID,
    payload: ZonePatch,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ZoneOut:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise DomainError("not_found", "Zona não encontrada.", status.HTTP_404_NOT_FOUND)
    if payload.name is not None:
        zone.name = payload.name
    if payload.cep_ranges is not None:
        zone.cep_ranges = _ranges(payload.cep_ranges)
    for field in ("delivery_fee", "min_order_value", "eta_minutes", "active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(zone, field, value)
    db.commit()
    return _to_out(zone)
