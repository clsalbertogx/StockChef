from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.service import default_store
from app.modules.delivery.models import Delivery, Driver, ProofOfDelivery, Zone
from app.modules.delivery.schemas import (
    CepRange,
    DeliveryAssign,
    DeliveryCreate,
    DeliveryOut,
    DeliveryStatusUpdate,
    DriverCreate,
    DriverOut,
    DriverPatch,
    ProofOfDeliveryCreate,
    ProofOfDeliveryOut,
    ZoneCreate,
    ZoneOut,
    ZonePatch,
)
from app.modules.delivery.service import (
    assign_driver as assign_driver_svc,
)
from app.modules.delivery.service import (
    create_delivery as create_delivery_svc,
)
from app.modules.delivery.service import (
    create_driver as create_driver_svc,
)
from app.modules.delivery.service import (
    deactivate_driver as deactivate_driver_svc,
)
from app.modules.delivery.service import (
    get_delivery as get_delivery_svc,
)
from app.modules.delivery.service import (
    get_delivery_by_order as get_delivery_by_order_svc,
)
from app.modules.delivery.service import (
    get_driver as get_driver_svc,
)
from app.modules.delivery.service import (
    get_driver_performance as get_driver_performance_svc,
)
from app.modules.delivery.service import (
    get_proof_of_delivery as get_proof_of_delivery_svc,
)
from app.modules.delivery.service import (
    list_deliveries as list_deliveries_svc,
)
from app.modules.delivery.service import (
    list_drivers as list_drivers_svc,
)
from app.modules.delivery.service import (
    submit_proof_of_delivery as submit_proof_of_delivery_svc,
)
from app.modules.delivery.service import (
    update_delivery_status as update_delivery_status_svc,
)
from app.modules.delivery.service import (
    update_driver as update_driver_svc,
)

router = APIRouter(tags=["entregas"])


def _tenant_id(db: Session) -> UUID:
    return db.info["tenant_id"]


def _to_out(z: Zone) -> ZoneOut:
    return ZoneOut(
        id=z.id, store_id=z.store_id, name=z.name, cep_ranges=z.cep_ranges or [],
        delivery_fee=z.delivery_fee, min_order_value=z.min_order_value,
        eta_minutes=z.eta_minutes, active=z.active,
    )


def _driver_to_out(d: Driver) -> DriverOut:
    return DriverOut(
        id=d.id, tenant_id=d.tenant_id, name=d.name, phone=d.phone,
        document=d.document, vehicle_type=d.vehicle_type, plate=d.plate,
        payment_model=d.payment_model, status=d.status,
        rating_average=d.rating_average, created_at=d.created_at, updated_at=d.updated_at,
    )


def _delivery_to_out(d: Delivery) -> DeliveryOut:
    return DeliveryOut(
        id=d.id, tenant_id=d.tenant_id, order_id=d.order_id, driver_id=d.driver_id,
        status=d.status, assigned_at=d.assigned_at, picked_up_at=d.picked_up_at,
        delivered_at=d.delivered_at, eta_minutes=d.eta_minutes,
        route_hint=d.route_hint, occurrence=d.occurrence,
        created_at=d.created_at, updated_at=d.updated_at,
    )


def _proof_to_out(p: ProofOfDelivery) -> ProofOfDeliveryOut:
    return ProofOfDeliveryOut(
        id=p.id, tenant_id=p.tenant_id, delivery_id=p.delivery_id,
        type=p.type, file_url=p.file_url, received_by=p.received_by, created_at=p.created_at,
    )


def _ranges(payload_ranges: list[CepRange]) -> list[dict]:
    return [{"start": r.start, "end": r.end} for r in payload_ranges]


# ===== Zonas =====

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


# ===== Drivers =====

@router.post("/entregadores", status_code=status.HTTP_201_CREATED)
def create_driver(
    payload: DriverCreate,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DriverOut:
    tid = _tenant_id(db)
    driver = create_driver_svc(
        db, tid, payload.name, payload.phone, payload.document,
        payload.vehicle_type, payload.plate, payload.payment_model,
    )
    return _driver_to_out(driver)


@router.get("/entregadores")
def list_drivers(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> list:
    tid = _tenant_id(db)
    drivers = list_drivers_svc(db, tid, status, limit, offset)
    return [_driver_to_out(d) for d in drivers]


@router.get("/entregadores/{driver_id}")
def get_driver(
    driver_id: UUID,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DriverOut:
    tid = _tenant_id(db)
    driver = get_driver_svc(db, tid, driver_id)
    if driver is None:
        raise DomainError("not_found", "Entregador não encontrado.", status.HTTP_404_NOT_FOUND)
    return _driver_to_out(driver)


@router.patch("/entregadores/{driver_id}")
def update_driver(
    driver_id: UUID,
    payload: DriverPatch,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DriverOut:
    tid = _tenant_id(db)
    driver = update_driver_svc(
        db, tid, driver_id,
        name=payload.name, phone=payload.phone, document=payload.document,
        vehicle_type=payload.vehicle_type, plate=payload.plate,
        payment_model=payload.payment_model, status=payload.status,
    )
    return _driver_to_out(driver)


@router.delete("/entregadores/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_driver(
    driver_id: UUID,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> None:
    tid = _tenant_id(db)
    deactivate_driver_svc(db, tid, driver_id)


# ===== Deliveries =====

@router.post("/entregas", status_code=status.HTTP_201_CREATED)
def create_delivery(
    payload: DeliveryCreate,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DeliveryOut:
    tid = _tenant_id(db)
    delivery = create_delivery_svc(
        db, tid, payload.order_id, payload.driver_id, payload.eta_minutes, payload.route_hint,
    )
    return _delivery_to_out(delivery)


@router.get("/entregas")
def list_deliveries(
    status: str | None = None,
    driver_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> list:
    tid = _tenant_id(db)
    deliveries = list_deliveries_svc(db, tid, status, driver_id, limit, offset)
    return [_delivery_to_out(d) for d in deliveries]


@router.get("/entregas/{delivery_id}")
def get_delivery(
    delivery_id: UUID,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DeliveryOut:
    tid = _tenant_id(db)
    delivery = get_delivery_svc(db, tid, delivery_id)
    if delivery is None:
        raise DomainError("not_found", "Entrega não encontrada.", status.HTTP_404_NOT_FOUND)
    return _delivery_to_out(delivery)


@router.get("/pedidos/{order_id}/entrega")
def get_delivery_by_order(
    order_id: UUID,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DeliveryOut:
    tid = _tenant_id(db)
    delivery = get_delivery_by_order_svc(db, tid, order_id)
    if delivery is None:
        raise DomainError(
            "not_found", "Entrega não encontrada para este pedido.", status.HTTP_404_NOT_FOUND
        )
    return _delivery_to_out(delivery)


@router.post("/entregas/{delivery_id}/atribuir")
def assign_driver(
    delivery_id: UUID,
    payload: DeliveryAssign,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DeliveryOut:
    tid = _tenant_id(db)
    delivery = assign_driver_svc(db, tid, delivery_id, payload.driver_id, actor.id)
    return _delivery_to_out(delivery)


@router.patch("/entregas/{delivery_id}/status")
def update_delivery_status(
    delivery_id: UUID,
    payload: DeliveryStatusUpdate,
    actor: Actor = Depends(require_roles("kitchen", "manager", "owner", "cashier")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> DeliveryOut:
    tid = _tenant_id(db)
    delivery = update_delivery_status_svc(
        db, tid, delivery_id, payload.status, actor.id, payload.occurrence
    )
    return _delivery_to_out(delivery)


# ===== Proof of Delivery =====

@router.post("/entregas/{delivery_id}/prova", status_code=status.HTTP_201_CREATED)
def submit_proof(
    delivery_id: UUID,
    payload: ProofOfDeliveryCreate,
    actor: Actor = Depends(require_roles("kitchen", "manager", "owner", "cashier")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ProofOfDeliveryOut:
    tid = _tenant_id(db)
    proof = submit_proof_of_delivery_svc(
        db, tid, delivery_id, payload.type, payload.file_url, payload.received_by, actor.id,
    )
    return _proof_to_out(proof)


@router.get("/entregas/{delivery_id}/prova")
def get_proof(
    delivery_id: UUID,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ProofOfDeliveryOut:
    tid = _tenant_id(db)
    proof = get_proof_of_delivery_svc(db, tid, delivery_id)
    if proof is None:
        raise DomainError(
            "not_found", "Prova de entrega não encontrada.", status.HTTP_404_NOT_FOUND
        )
    return _proof_to_out(proof)


# ===== Driver Performance =====

@router.get("/entregadores/{driver_id}/desempenho")
def driver_performance(
    driver_id: UUID,
    days: int = 30,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> dict:
    tid = _tenant_id(db)
    return get_driver_performance_svc(db, tid, driver_id, days)