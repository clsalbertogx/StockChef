from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import current_actor, get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.models import Product, StockMovement, Store
from app.modules.catalog.service import default_store
from app.modules.inventory.service import apply_movement, ensure_stock_level
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem, OutboxEvent, Payment
from app.modules.orders.outbox import drain_outbox
from app.modules.orders.schemas import (
    KitchenItemOut,
    KitchenOrderOut,
    OrderCancel,
    OrderCreate,
    OrderItemOut,
    OrderOut,
    OrderStatusUpdate,
)
from app.modules.orders.service import availability, availability_ok, recipe_snapshot
from app.modules.storefront.service import _resolve_modifiers

router = APIRouter(tags=["pedidos"])

TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    ("confirmed", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("confirmed_pending_stock", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("preparing", "ready"): frozenset({"kitchen", "manager", "owner"}),
    ("ready", "delivered"): frozenset({"cashier", "manager", "owner"}),
    ("ready", "completed"): frozenset({"cashier", "manager", "owner"}),
    ("delivered", "completed"): frozenset({"owner", "manager"}),
}

CANCELLABLE = ("received", "confirmed", "confirmed_pending_stock", "preparing", "ready")
CANCEL_BLOCKED = ("delivered", "completed", "refunded")


def _tenant_id(db: Session) -> UUID:
    """Tenant ativo da sessão — setado por get_tenant_db (app.core.deps)."""
    return db.info["tenant_id"]


def _require_store(db: Session, tid: UUID, store_id: UUID) -> UUID:
    store = db.get(Store, store_id)
    if store is None or store.tenant_id != UUID(str(tid)):
        raise DomainError("store_not_found", "Loja não encontrada.", status.HTTP_404_NOT_FOUND)
    return store.id


def _gen_code(db: Session, store_id: UUID) -> str:
    import secrets

    for _ in range(5):
        code = f"SC-{secrets.token_hex(6).upper()}"
        if not db.scalar(select(Order).where(Order.code == code)):
            return code
    raise DomainError(
        "code_conflict",
        "Não foi possível gerar um código único.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _upsert_customer(
    db: Session, tid: UUID, name: str | None, phone: str | None
) -> Customer | None:
    if not phone and not name:
        return None
    if phone:
        cust = db.scalar(
            select(Customer).where(Customer.tenant_id == tid, Customer.phone == phone)
        )
        if cust is not None:
            if name:
                cust.name = name
            return cust
    cust = Customer(tenant_id=tid, name=name, phone=phone)
    db.add(cust)
    db.flush()
    return cust


def _to_out(db: Session, order: Order) -> OrderOut:
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    out_items = []
    for it in items:
        product = db.get(Product, it.product_id)
        if product is None:  # FK RESTRICT impede deleção; defesa p/ robustez
            raise DomainError(
                "not_found", "Produto do pedido não encontrado.", status.HTTP_404_NOT_FOUND
            )
        out_items.append(
            OrderItemOut(
                product_id=it.product_id,
                product_name=product.name,
                quantity=it.quantity,
                unit_price=it.unit_price,
                total_price=it.total_price,
                notes=it.notes,
                modifiers=it.modifiers or [],
            )
        )
    cust = db.get(Customer, order.customer_id) if order.customer_id else None
    return OrderOut(
        id=order.id,
        code=order.code,
        status=order.status,
        customer_name=cust.name if cust else None,
        customer_phone=cust.phone if cust else None,
        channel=order.channel,
        fulfillment_type=order.fulfillment_type,
        expected_time=order.expected_time,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount_total=order.discount_total,
        tax_total=order.tax_total,
        total=order.total,
        notes=order.notes,
        created_at=order.created_at,
        order_items=out_items,
    )


@router.post("/pedidos", status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_tenant_db)) -> OrderOut:  # noqa: B008
    tid = _tenant_id(db)
    store_id = (
        _require_store(db, tid, payload.store_id)
        if payload.store_id
        else default_store(db, tid).id
    )
    availability(
        db,
        store_id,
        [(it.product_id, it.quantity) for it in payload.items],
    )

    customer = _upsert_customer(db, tid, payload.customer_name, payload.customer_phone)
    order = Order(
        tenant_id=tid,
        store_id=store_id,
        customer_id=customer.id if customer else None,
        code=_gen_code(db, store_id),
        status="received",
        channel=payload.channel,
        fulfillment_type=payload.fulfillment_type,
        notes=payload.notes,
        expected_time=payload.scheduled_time,
    )
    db.add(order)
    db.flush()

    subtotal = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        if product is None:
            raise DomainError(
                "not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND
            )
        # Resolve modificadores
        chosen, delta = _resolve_modifiers(db, product, it.modifier_ids)
        unit = (product.price + delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line = (unit * it.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += line
        db.add(
            OrderItem(
                tenant_id=tid,
                order_id=order.id,
                product_id=it.product_id,
                quantity=it.quantity,
                unit_price=unit,
                total_price=line,
                notes=it.notes,
                modifiers=[
                    {
                        "product_modifier_id": str(m.id),
                        "group_name": m.group_name,
                        "name": m.modifier_name,
                        "price_delta": str(m.price_delta),
                        "quantity": 1,
                        "id": str(m.id),
                        "modifier_name": m.modifier_name,
                    }
                    for m in chosen
                ],
                recipe_snapshot=recipe_snapshot(db, it.product_id),
            )
        )
    order.subtotal = subtotal
    order.total = subtotal
    db.add(
        OrderEvent(
            tenant_id=tid,
            order_id=order.id,
            event_type="order.created",
            from_status=None,
            to_status="received",
        )
    )
    db.commit()
    return _to_out(db, order)


@router.get("/pedidos")
def list_orders(db: Session = Depends(get_tenant_db)) -> list[OrderOut]:  # noqa: B008
    rows = db.scalars(
        select(Order)
        .where(Order.tenant_id == _tenant_id(db))
        .order_by(Order.created_at.desc())
    ).all()
    return [_to_out(db, o) for o in rows]


@router.get("/pedidos/{order_id}")
def get_order(order_id: UUID, db: Session = Depends(get_tenant_db)) -> OrderOut:  # noqa: B008
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    return _to_out(db, order)


def _items_of(db: Session, order_id: UUID) -> Sequence[OrderItem]:
    return db.scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all()


@router.post("/pedidos/{order_id}/confirmar")
def confirm_order(
    order_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if order.status in ("confirmed", "confirmed_pending_stock"):
        return _to_out(db, order)  # idempotente
    if order.status != "received":
        raise DomainError(
            "invalid_state",
            "Pedido não pode ser confirmado nesse estado.",
            status.HTTP_409_CONFLICT,
        )

    ok = availability_ok(
        db,
        order.store_id,
        [(i.product_id, i.quantity) for i in _items_of(db, order.id)],
    )
    order.status = "confirmed" if ok else "confirmed_pending_stock"
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="status.changed",
                      from_status="received", to_status=order.status))
    # evento de domínio `order.confirmed` — casa com o event_type do outbox (§6.5)
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="order.confirmed",
                      from_status="received", to_status=order.status))
    db.add(
        OutboxEvent(
            tenant_id=tid,
            event_type="order.confirmed",
            payload={"order_id": str(order.id)},
            idempotency_key=f"order.confirmed:{order.id}",
        )
    )
    # Cria pagamento (cash on delivery por padrão) — idempotente
    existing_payment = db.scalar(
        select(Payment).where(Payment.order_id == order.id)
    )
    if existing_payment is None:
        db.add(Payment(
            tenant_id=tid, order_id=order.id, provider="cash", method="cash", amount=order.total,
            status="pending", idempotency_key=f"order.payment:{order.id}",
        ))
    db.commit()
    background_tasks.add_task(drain_outbox, tid)
    return _to_out(db, order)


@router.patch("/pedidos/{order_id}/status")
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    actor: Actor = Depends(current_actor),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if payload.status == order.status:
        return _to_out(db, order)  # no-op idempotente
    roles = TRANSITIONS.get((order.status, payload.status))
    if roles is None:
        raise DomainError(
            "invalid_state", "Transição de status inválida.", status.HTTP_409_CONFLICT
        )
    if actor.role not in roles:
        raise DomainError("forbidden", "Permissão insuficiente.", status.HTTP_403_FORBIDDEN)
    old = order.status
    order.status = payload.status
    order.updated_at = datetime.now(UTC)
    db.add(
        OrderEvent(
            tenant_id=tid,
            order_id=order.id,
            event_type="status.changed",
            from_status=old,
            to_status=payload.status,
            user_id=actor.id,
            payload={"notes": payload.notes} if payload.notes else {},
        )
    )
    db.commit()
    return _to_out(db, order)


@router.get("/pedidos/{order_id}/eventos")
def order_events(order_id: UUID, db: Session = Depends(get_tenant_db)) -> dict:  # noqa: B008
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    events = db.scalars(
        select(OrderEvent).where(OrderEvent.order_id == order_id).order_by(OrderEvent.created_at)
    ).all()
    outbox = db.scalars(
        select(OutboxEvent).where(OutboxEvent.payload["order_id"].astext == str(order_id))
    ).all()
    outbox_status = {o.event_type: o.status for o in outbox}
    return {
        "order_id": str(order_id),
        "status": order.status,
        "events": [
            {
                "event_type": e.event_type, "from_status": e.from_status, "to_status": e.to_status,
                "created_at": e.created_at.isoformat(),
                "outbox_status": outbox_status.get(e.event_type),
            }
            for e in events
        ],
    }


@router.post("/pedidos/{order_id}/cancelar")
def cancel_order(
    order_id: UUID,
    payload: OrderCancel,
    actor: Actor = Depends(current_actor),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if order.status == "cancelled":
        return _to_out(db, order)  # idempotente
    if order.status in CANCEL_BLOCKED or order.status not in CANCELLABLE:
        raise DomainError(
            "invalid_state", "Pedido não pode ser cancelado nesse estado.",
            status.HTTP_409_CONFLICT,
        )
    if actor.role not in ("owner", "manager", "cashier"):
        raise DomainError("forbidden", "Permissão insuficiente.", status.HTTP_403_FORBIDDEN)

    sales = db.scalars(
        select(StockMovement).where(
            StockMovement.reference_type == "order",
            StockMovement.reference_id == order.id,
            StockMovement.type == "sale",
        )
    ).all()
    for mov in sales:
        ensure_stock_level(
            db, tenant_id=tid, store_id=order.store_id, ingredient_id=mov.ingredient_id
        )
        apply_movement(
            db,
            tenant_id=tid,
            store_id=order.store_id,
            ingredient_id=mov.ingredient_id,
            type_="reversal",
            quantity=abs(mov.quantity),
            unit_cost=mov.unit_cost,
            reference_type="order",
            reference_id=order.id,
            reason="Cancelamento de pedido",
            idempotency_key=f"order.reversed:{order.id}:{mov.ingredient_id}",
            user_id=actor.id,
        )

    old = order.status
    order.status = "cancelled"
    order.updated_at = datetime.now(UTC)
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="status.changed",
                      from_status=old, to_status="cancelled", user_id=actor.id))
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="order.cancelled",
                      from_status=old, to_status="cancelled", user_id=actor.id,
                      payload={"motivo": payload.motivo}))
    db.commit()
    return _to_out(db, order)


KDS_STATUSES = ("confirmed", "confirmed_pending_stock", "preparing")


@router.get("/cozinha/fila")
def kitchen_queue(
    actor: Actor = Depends(require_roles("kitchen", "manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> list[KitchenOrderOut]:
    tid = _tenant_id(db)
    orders = db.scalars(
        select(Order)
        .where(Order.tenant_id == tid, Order.status.in_(KDS_STATUSES))
        .order_by(Order.created_at.asc())
    ).all()
    if not orders:
        return []
    order_ids = [o.id for o in orders]
    rows = db.execute(
        select(OrderItem, Product.name)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.order_id.in_(order_ids))
    ).all()
    by_order: dict[UUID, list[KitchenItemOut]] = {}
    for item, product_name in rows:
        by_order.setdefault(item.order_id, []).append(
            KitchenItemOut(
                order_item_id=item.id,
                product_name=product_name,
                quantity=item.quantity,
                notes=item.notes,
                modifiers=item.modifiers or [],
            )
        )
    now = datetime.now(UTC)
    return [
        KitchenOrderOut(
            order_id=o.id,
            code=o.code,
            status=o.status,
            channel=o.channel,
            fulfillment_type=o.fulfillment_type,
            notes=o.notes,
            created_at=o.created_at,
            elapsed_minutes=max(0, int((now - o.created_at).total_seconds() // 60)),
            items=by_order.get(o.id, []),
        )
        for o in orders
    ]
