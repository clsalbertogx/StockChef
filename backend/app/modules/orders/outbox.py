from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, set_tenant
from app.modules.catalog.models import StockLevel, StockMovement
from app.modules.orders.models import Order, OrderEvent, OrderItem, OutboxEvent


def drain_outbox(tenant_id: UUID) -> None:
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)
        while True:
            event = db.scalar(
                select(OutboxEvent)
                .where(OutboxEvent.tenant_id == tenant_id, OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if event is None:
                break
            _process(db, tenant_id, event)
            db.commit()
    finally:
        db.close()


def _process(db: Session, tenant_id: UUID, event: OutboxEvent) -> None:
    if event.event_type != "order.confirmed":
        event.status = "failed"
        event.last_error = "unsupported event type"
        return

    order = db.get(Order, UUID(event.payload["order_id"]))
    if order is None:
        event.status = "failed"
        event.last_error = "order not found"
        return

    required: defaultdict[UUID, Decimal] = defaultdict(Decimal)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for item in items:
        for snap in item.recipe_snapshot:
            required[UUID(snap["ingredient_id"])] += item.quantity * Decimal(snap["quantity"])

    # movimentos já existentes para o pedido (idempotência: reprocessar é no-op)
    done = set(
        db.scalars(
            select(StockMovement.ingredient_id).where(
                StockMovement.reference_type == "order", StockMovement.reference_id == order.id
            )
        ).all()
    )
    remaining = {i: n for i, n in required.items() if n > 0 and i not in done}
    if not remaining:
        event.status = "processed"
        event.processed_at = datetime.now(UTC)
        return

    rows: dict[UUID, StockLevel | None] = {}
    for ingredient_id in remaining:
        sl = db.scalar(
            select(StockLevel)
            .where(StockLevel.store_id == order.store_id, StockLevel.ingredient_id == ingredient_id)
            .with_for_update()
        )
        rows[ingredient_id] = sl

    if any(sl is None or sl.quantity < remaining[i] for i, sl in rows.items()):
        order.status = "confirmed_pending_stock"
        db.add(OrderEvent(
            tenant_id=tenant_id, order_id=order.id, event_type="inventory.shortage",
            from_status="confirmed", to_status="confirmed_pending_stock",
            payload={"detail": "Estoque insuficiente no momento da baixa."},
        ))
        event.status = "failed"
        event.last_error = "insufficient stock"
        return

    for ingredient_id, need in remaining.items():
        sl = rows[ingredient_id]
        assert sl is not None
        db.execute(
            update(StockLevel)
            .where(StockLevel.id == sl.id, StockLevel.quantity >= need)
            .values(quantity=StockLevel.quantity - need)
        )
        db.add(StockMovement(
            tenant_id=tenant_id, store_id=order.store_id, ingredient_id=ingredient_id,
            type="sale", quantity=-need, unit_cost=sl.average_cost,
            reference_type="order", reference_id=order.id,
            idempotency_key=f"order.confirmed:{order.id}:{ingredient_id}",
        ))

    event.status = "processed"
    event.processed_at = datetime.now(UTC)
