from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.models import Product
from app.modules.catalog.service import default_store
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem
from app.modules.orders.schemas import OrderCreate, OrderItemOut, OrderOut
from app.modules.orders.service import availability, recipe_snapshot

router = APIRouter(tags=["pedidos"])


def _tenant_id(db: Session) -> UUID:
    """Tenant ativo da sessão — setado por get_tenant_db (app.core.deps)."""
    return db.info["tenant_id"]


def _gen_code(db: Session, store_id: UUID) -> str:
    import secrets

    return f"SC-{secrets.token_hex(4).upper()}"


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
        assert product is not None  # FK de order_items garante existência
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
    store_id = payload.store_id or default_store(db, tid).id
    availability(
        db,
        tid,
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
        assert product is not None
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
