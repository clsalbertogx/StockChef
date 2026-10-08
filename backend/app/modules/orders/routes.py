from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.models import Product, Store
from app.modules.catalog.service import default_store
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem, OutboxEvent
from app.modules.orders.outbox import drain_outbox
from app.modules.orders.schemas import OrderCreate, OrderItemOut, OrderOut
from app.modules.orders.service import availability, availability_ok, recipe_snapshot

router = APIRouter(tags=["pedidos"])


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
            )
        )
    cust = db.get(Customer, order.customer_id) if order.customer_id else None
    return OrderOut(
        id=order.id,
        code=order.code,
        status=order.status,
        customer_name=cust.name if cust else None,
        customer_phone=cust.phone if cust else None,
        subtotal=order.subtotal,
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
        unit_price = product.price
        total_price = unit_price * it.quantity
        subtotal += total_price
        db.add(
            OrderItem(
                tenant_id=tid,
                order_id=order.id,
                product_id=it.product_id,
                quantity=it.quantity,
                unit_price=unit_price,
                total_price=total_price,
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
    db.commit()
    background_tasks.add_task(drain_outbox, tid)
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
