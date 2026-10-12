from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.delivery.models import Delivery, Driver, ProofOfDelivery, Zone
from app.modules.orders.models import Order, OrderEvent


def normalize_cep(cep: str) -> str:
    return "".join(ch for ch in cep if ch.isdigit())


def resolve_zone(db: Session, store_id: UUID, cep: str) -> Zone | None:
    normalized = normalize_cep(cep)
    if len(normalized) != 8:
        return None
    zones = db.scalars(
        select(Zone).where(Zone.store_id == store_id, Zone.active.is_(True))
    ).all()
    for zone in zones:
        for rng in zone.cep_ranges or []:
            start = normalize_cep(str(rng.get("start", "")))
            end = normalize_cep(str(rng.get("end", "")))
            if len(start) == 8 and len(end) == 8 and start <= normalized <= end:
                return zone
    return None


# ===== Driver Service =====


def create_driver(
    db: Session,
    tenant_id: UUID,
    name: str,
    phone: str,
    document: str | None,
    vehicle_type: str,
    plate: str | None,
    payment_model: str,
) -> Driver:
    """Cria um novo entregador."""
    # Verifica se já existe entregador com mesmo phone no tenant
    existing = db.scalar(
        select(Driver).where(Driver.tenant_id == tenant_id, Driver.phone == phone)
    )
    if existing:
        raise DomainError(
            "driver_phone_taken", "Já existe um entregador com esse telefone.",
            409,
        )

    driver = Driver(
        tenant_id=tenant_id,
        name=name,
        phone=phone,
        document=document,
        vehicle_type=vehicle_type,
        plate=plate,
        payment_model=payment_model,
        status="active",
        rating_average=Decimal("5.00"),
    )
    db.add(driver)
    db.flush()
    return driver


def get_driver(db: Session, tenant_id: UUID, driver_id: UUID) -> Driver | None:
    """Obtém um entregador por ID (com verificação de tenant)."""
    return db.scalar(
        select(Driver).where(Driver.id == driver_id, Driver.tenant_id == tenant_id)
    )


def list_drivers(
    db: Session,
    tenant_id: UUID,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Driver]:
    """Lista entregadores do tenant."""
    query = select(Driver).where(Driver.tenant_id == tenant_id)
    if status:
        query = query.where(Driver.status == status)
    query = query.order_by(Driver.name).limit(limit).offset(offset)
    return db.scalars(query).all()


def update_driver(
    db: Session,
    tenant_id: UUID,
    driver_id: UUID,
    name: str | None = None,
    phone: str | None = None,
    document: str | None = None,
    vehicle_type: str | None = None,
    plate: str | None = None,
    payment_model: str | None = None,
    status: str | None = None,
) -> Driver:
    """Atualiza dados do entregador."""
    driver = get_driver(db, tenant_id, driver_id)
    if driver is None:
        raise DomainError("not_found", "Entregador não encontrado.", 404)

    if phone is not None and phone != driver.phone:
        existing = db.scalar(
            select(Driver).where(
                Driver.tenant_id == tenant_id, Driver.phone == phone, Driver.id != driver_id
            )
        )
        if existing:
            raise DomainError(
                "driver_phone_taken", "Já existe um entregador com esse telefone.", 409
            )
        driver.phone = phone

    if name is not None:
        driver.name = name
    if document is not None:
        driver.document = document
    if vehicle_type is not None:
        driver.vehicle_type = vehicle_type
    if plate is not None:
        driver.plate = plate
    if payment_model is not None:
        driver.payment_model = payment_model
    if status is not None:
        driver.status = status

    db.flush()
    return driver


def deactivate_driver(db: Session, tenant_id: UUID, driver_id: UUID) -> Driver:
    """Desativa um entregador (soft delete)."""
    driver = get_driver(db, tenant_id, driver_id)
    if driver is None:
        raise DomainError("not_found", "Entregador não encontrado.", 404)
    driver.status = "inactive"
    db.flush()
    return driver


# ===== Delivery Service =====


def create_delivery(
    db: Session,
    tenant_id: UUID,
    order_id: UUID,
    driver_id: UUID | None = None,
    eta_minutes: int | None = None,
    route_hint: dict | None = None,
) -> Delivery:
    """Cria uma entrega para um pedido."""
    # Verifica se o pedido existe e pertence ao tenant
    order = db.get(Order, order_id)
    if order is None or str(order.tenant_id) != str(tenant_id):
        raise DomainError("not_found", "Pedido não encontrado.", 404)

    # Verifica se já existe entrega para este pedido
    existing = db.scalar(
        select(Delivery).where(Delivery.order_id == order_id)
    )
    if existing:
        raise DomainError(
            "delivery_exists", "Já existe uma entrega para este pedido.", 409
        )

    # Se driver_id informado, valida
    if driver_id:
        driver = get_driver(db, tenant_id, driver_id)
        if driver is None:
            raise DomainError("not_found", "Entregador não encontrado.", 404)
        if driver.status != "active":
            raise DomainError("driver_inactive", "Entregador não está ativo.", 409)

    # Calcula ETA se não informado
    if eta_minutes is None:
        # Usa ETA da zona se for delivery
        eta_minutes = 30  # fallback

    delivery = Delivery(
        tenant_id=tenant_id,
        order_id=order_id,
        driver_id=driver_id,
        status="pending",
        eta_minutes=eta_minutes,
        route_hint=route_hint or {},
    )
    db.add(delivery)
    db.flush()
    return delivery


def get_delivery(db: Session, tenant_id: UUID, delivery_id: UUID) -> Delivery | None:
    """Obtém uma entrega por ID (com verificação de tenant)."""
    return db.scalar(
        select(Delivery).where(
            Delivery.id == delivery_id, Delivery.tenant_id == tenant_id
        )
    )


def get_delivery_by_order(db: Session, tenant_id: UUID, order_id: UUID) -> Delivery | None:
    """Obtém a entrega associada a um pedido."""
    return db.scalar(
        select(Delivery).where(
            Delivery.order_id == order_id, Delivery.tenant_id == tenant_id
        )
    )


def list_deliveries(
    db: Session,
    tenant_id: UUID,
    status: str | None = None,
    driver_id: UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Delivery]:
    """Lista entregas do tenant com filtros opcionais."""
    query = select(Delivery).where(Delivery.tenant_id == tenant_id)
    if status:
        query = query.where(Delivery.status == status)
    if driver_id:
        query = query.where(Delivery.driver_id == driver_id)
    query = query.order_by(Delivery.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(query).all()


def assign_driver(
    db: Session,
    tenant_id: UUID,
    delivery_id: UUID,
    driver_id: UUID,
    actor_id: UUID,
) -> Delivery:
    """Atribui um entregador a uma entrega."""
    delivery = get_delivery(db, tenant_id, delivery_id)
    if delivery is None:
        raise DomainError("not_found", "Entrega não encontrada.", 404)

    driver = get_driver(db, tenant_id, driver_id)
    if driver is None:
        raise DomainError("not_found", "Entregador não encontrado.", 404)
    if driver.status != "active":
        raise DomainError("driver_inactive", "Entregador não está ativo.", 409)

    if delivery.status not in ("pending", "assigned"):
        raise DomainError(
            "invalid_state",
            f"Não é possível atribuir entregador no estado '{delivery.status}'.",
            409,
        )

    delivery.driver_id = driver_id
    delivery.status = "assigned"
    delivery.assigned_at = datetime.now(UTC)

    db.add(OrderEvent(
        tenant_id=tenant_id,
        order_id=delivery.order_id,
        event_type="delivery.assigned",
        from_status=delivery.status,
        to_status="assigned",
        user_id=actor_id,
        payload={"driver_id": str(driver_id)},
    ))
    db.flush()
    return delivery


def update_delivery_status(
    db: Session,
    tenant_id: UUID,
    delivery_id: UUID,
    status: str,
    actor_id: UUID,
    occurrence: str | None = None,
) -> Delivery:
    """Atualiza o status de uma entrega."""
    valid_statuses = [
        "pending",
        "assigned",
        "picked_up",
        "in_transit",
        "delivered",
        "failed",
        "canceled",
    ]
    if status not in valid_statuses:
        raise DomainError("invalid_status", "Status inválido.", 422)

    delivery = get_delivery(db, tenant_id, delivery_id)
    if delivery is None:
        raise DomainError("not_found", "Entrega não encontrada.", 404)

    # Valida transições de status
    valid_transitions = {
        "pending": ["assigned", "canceled"],
        "assigned": ["picked_up", "canceled"],
        "picked_up": ["in_transit", "canceled"],
        "in_transit": ["delivered", "failed"],
        "delivered": [],
        "failed": [],
        "canceled": [],
    }

    if status not in valid_transitions.get(delivery.status, []):
        raise DomainError(
            "invalid_transition",
            f"Transição inválida: {delivery.status} -> {status}",
            409,
        )

    old_status = delivery.status
    delivery.status = status
    delivery.updated_at = datetime.now(UTC)

    now = datetime.now(UTC)
    if status == "picked_up":
        delivery.picked_up_at = now
    elif status == "delivered":
        delivery.delivered_at = now

    if occurrence:
        delivery.occurrence = occurrence

    db.add(OrderEvent(
        tenant_id=tenant_id,
        order_id=delivery.order_id,
        event_type="delivery.status.changed",
        from_status=old_status,
        to_status=status,
        user_id=actor_id,
        payload={"occurrence": occurrence} if occurrence else {},
    ))
    db.flush()
    return delivery


# ===== Proof of Delivery Service =====


def submit_proof_of_delivery(
    db: Session,
    tenant_id: UUID,
    delivery_id: UUID,
    type_: str,
    file_url: str | None,
    received_by: str | None,
    actor_id: UUID,
) -> ProofOfDelivery:
    """Registra prova de entrega."""
    delivery = get_delivery(db, tenant_id, delivery_id)
    if delivery is None:
        raise DomainError("not_found", "Entrega não encontrada.", 404)

    if delivery.status != "delivered":
        raise DomainError(
            "invalid_state",
            "Prova de entrega só pode ser registrada para entregas com status 'delivered'.",
            409,
        )

    valid_types = ["photo", "signature", "pin", "customer_confirmation"]
    if type_ not in valid_types:
        raise DomainError("invalid_type", "Tipo de prova inválido.", 422)

    proof = ProofOfDelivery(
        tenant_id=tenant_id,
        delivery_id=delivery_id,
        type=type_,
        file_url=file_url,
        received_by=received_by,
    )
    db.add(proof)

    db.add(OrderEvent(
        tenant_id=tenant_id,
        order_id=delivery.order_id,
        event_type="delivery.proof_submitted",
        from_status=delivery.status,
        to_status=delivery.status,
        user_id=actor_id,
        payload={"proof_type": type_, "received_by": received_by},
    ))
    db.flush()
    return proof


def get_proof_of_delivery(
    db: Session, tenant_id: UUID, delivery_id: UUID
) -> ProofOfDelivery | None:
    """Obtém a prova de entrega."""
    return db.scalar(
        select(ProofOfDelivery).where(
            ProofOfDelivery.delivery_id == delivery_id,
            ProofOfDelivery.tenant_id == tenant_id,
        )
    )


def get_driver_performance(
    db: Session,
    tenant_id: UUID,
    driver_id: UUID,
    days: int = 30,
) -> dict:
    """Obtém métricas de desempenho do entregador."""
    driver = get_driver(db, tenant_id, driver_id)
    if driver is None:
        raise DomainError("not_found", "Entregador não encontrado.", 404)

    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Total de entregas no período
    total = db.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.driver_id == driver_id,
            Delivery.tenant_id == tenant_id,
            Delivery.created_at >= cutoff,
        )
    ) or 0

    # Entregas concluídas
    completed = db.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.driver_id == driver_id,
            Delivery.tenant_id == tenant_id,
            Delivery.status == "delivered",
            Delivery.created_at >= cutoff,
        )
    ) or 0

    # Entregas falhadas
    failed = db.scalar(
        select(func.count(Delivery.id)).where(
            Delivery.driver_id == driver_id,
            Delivery.tenant_id == tenant_id,
            Delivery.status == "failed",
            Delivery.created_at >= cutoff,
        )
    ) or 0

    # Tempo médio de entrega (se disponível)
    avg_time = db.scalar(
        select(func.avg(
            func.extract("epoch", Delivery.delivered_at - Delivery.picked_up_at) / 60
        )).where(
            Delivery.driver_id == driver_id,
            Delivery.tenant_id == tenant_id,
            Delivery.status == "delivered",
            Delivery.picked_up_at.isnot(None),
            Delivery.delivered_at.isnot(None),
            Delivery.created_at >= cutoff,
        )
    )

    return {
        "driver_id": str(driver_id),
        "driver_name": driver.name,
        "period_days": days,
        "total_deliveries": total,
        "completed": completed,
        "failed": failed,
        "success_rate": round((completed / total * 100), 2) if total > 0 else 0,
        "avg_delivery_time_minutes": round(avg_time, 2) if avg_time else None,
    }