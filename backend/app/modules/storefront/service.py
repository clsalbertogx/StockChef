from __future__ import annotations

import math
import secrets
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import Category, Product, ProductModifier, Store
from app.modules.catalog.service import default_store
from app.modules.delivery.models import Zone
from app.modules.delivery.service import resolve_zone
from app.modules.identity.models import Tenant
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem, OutboxEvent, Payment
from app.modules.orders.service import availability, recipe_snapshot
from app.modules.storefront.schemas import (
    ModifierOut,
    PublicCategoryOut,
    PublicMenuOut,
    PublicOrderConfirm,
    PublicOrderCreate,
    PublicOrderItemOut,
    PublicOrderOut,
    PublicProductOut,
    PublicStoreOut,
    PublicTenantOut,
)


def _modifiers(db: Session, product_id: UUID) -> list[ModifierOut]:
    rows = db.scalars(
        select(ProductModifier)
        .where(ProductModifier.product_id == product_id, ProductModifier.active.is_(True))
        .order_by(ProductModifier.group_name, ProductModifier.modifier_name)
    ).all()
    return [
        ModifierOut(
            id=m.id, group_name=m.group_name, modifier_name=m.modifier_name,
            price_delta=m.price_delta, required=m.required,
            min_selection=m.min_selection, max_selection=m.max_selection,
        )
        for m in rows
    ]


def public_menu(
    db: Session, tenant: Tenant, store: Store, q: str | None, category_id: UUID | None
) -> PublicMenuOut:
    query = select(Product).where(Product.store_id == store.id, Product.active.is_(True))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    products = db.scalars(query.order_by(Product.name)).all()

    categories = db.scalars(
        select(Category)
        .where(Category.tenant_id == tenant.id, Category.active.is_(True))
        .order_by(Category.sort_order)
    ).all()

    return PublicMenuOut(
        tenant=PublicTenantOut(name=tenant.name, slug=tenant.slug),
        store=PublicStoreOut(
            id=store.id, name=store.name, delivery_enabled=store.delivery_enabled,
            pickup_enabled=store.pickup_enabled,
        ),
        categories=[
            PublicCategoryOut(id=c.id, name=c.name, sort_order=c.sort_order) for c in categories
        ],
        products=[
            PublicProductOut(
                id=p.id, name=p.name, description=p.description, price=p.price,
                image_url=p.image_url, category_id=p.category_id,
                preparation_time_minutes=p.preparation_time_minutes,
                modifiers=_modifiers(db, p.id),
            )
            for p in products
        ],
    )


def current_store(db: Session, tenant_id: UUID) -> Store:
    return default_store(db, tenant_id)


def _check_availability(
    db: Session, store_id: UUID, items: list[tuple[UUID, int]]
) -> None:
    """Valida estoque quando há ficha ativa; produtos sem ficha não são controlados."""
    try:
        availability(db, store_id, items)
    except DomainError as exc:
        if exc.code == "recipe_missing":
            return
        raise


def _snapshot(db: Session, product_id: UUID) -> list[dict]:
    """Captura a ficha técnica ativa; vazio quando o produto não tem ficha ativa."""
    try:
        return recipe_snapshot(db, product_id)
    except DomainError as exc:
        if exc.code == "recipe_missing":
            return []
        raise


def _gen_code(db: Session, store_id: UUID) -> str:
    for _ in range(5):
        code = f"SC-{secrets.token_hex(6).upper()}"
        if not db.scalar(select(Order).where(Order.code == code)):
            return code
    raise DomainError(
        "code_conflict", "Não foi possível gerar um código.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _upsert_customer(db: Session, tid: UUID, name: str, phone: str, address: dict) -> Customer:
    cust = db.scalar(
        select(Customer).where(Customer.tenant_id == tid, Customer.phone == phone)
    )
    if cust is None:
        cust = Customer(tenant_id=tid, name=name, phone=phone, address=address)
        db.add(cust)
        db.flush()
    else:
        cust.name = name
        if address:
            cust.address = address
    return cust


def _resolve_modifiers(
    db: Session, product: Product, modifier_ids: list[UUID]
) -> tuple[list[ProductModifier], Decimal]:
    mods = db.scalars(
        select(ProductModifier).where(
            ProductModifier.product_id == product.id, ProductModifier.active.is_(True)
        )
    ).all()
    by_id = {m.id: m for m in mods}
    chosen = []
    seen: set[UUID] = set()
    for mid in modifier_ids:
        if mid in seen:
            raise DomainError(
                "invalid_modifiers", "Adicional duplicado no pedido.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        seen.add(mid)
        mod = by_id.get(mid)
        if mod is None:
            raise DomainError(
                "invalid_modifiers", "Adicional inválido para o produto.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        chosen.append(mod)
    groups: defaultdict[str, list[ProductModifier]] = defaultdict(list)
    for mod in mods:
        groups[mod.group_name].append(mod)
    for group_name, group_mods in groups.items():
        selected = [m for m in chosen if m.group_name == group_name]
        required = any(m.required for m in group_mods)
        min_sel = max([m.min_selection for m in group_mods] or [0])
        maxes = [m.max_selection for m in group_mods if m.max_selection is not None]
        max_sel = min(maxes) if maxes else None
        if required and len(selected) < max(min_sel, 1):
            raise DomainError(
                "invalid_modifiers", f"Escolha obrigatória no grupo '{group_name}'.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if len(selected) < min_sel or (max_sel is not None and len(selected) > max_sel):
            raise DomainError(
                "invalid_modifiers", f"Seleção inválida no grupo '{group_name}'.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
    delta = sum((m.price_delta for m in chosen), Decimal("0"))
    return chosen, delta


def create_public_order(
    db: Session, tenant: Tenant, store: Store, payload: PublicOrderCreate
) -> Order:
    existing = db.scalar(
        select(Payment).where(
            Payment.idempotency_key == f"order.public:{payload.idempotency_key}"
        )
    )
    if existing is not None:
        return db.get(Order, existing.order_id)  # type: ignore[return-value]

    if payload.fulfillment_type == "delivery" and not store.delivery_enabled:
        raise DomainError(
            "fulfillment_unavailable", "Entrega não disponível para esta loja.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    if payload.fulfillment_type == "pickup" and not store.pickup_enabled:
        raise DomainError(
            "fulfillment_unavailable", "Retirada não disponível para esta loja.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    tid = tenant.id
    if payload.fulfillment_type == "delivery":
        if not payload.cep or not payload.address:
            raise DomainError(
                "address_required", "Endereço é obrigatório para entrega.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        zone = resolve_zone(db, store.id, payload.cep)
        has_zones = bool(
            db.scalar(select(Zone.id).where(Zone.store_id == store.id, Zone.active.is_(True)))
        )
        if zone is None and has_zones:
            raise DomainError(
                "cep_not_covered", "Não entregamos nesse CEP.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        delivery_fee = zone.delivery_fee if zone else Decimal("0.00")
        min_order = zone.min_order_value if zone else Decimal("0")
        eta = zone.eta_minutes if zone else 30
    else:
        delivery_fee = Decimal("0.00")
        min_order = Decimal("0")
        eta = 0

    resolved = []
    subtotal = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        if product is None or product.store_id != store.id or not product.active:
            raise DomainError(
                "product_not_found", "Produto não encontrado.",
                status.HTTP_404_NOT_FOUND,
            )
        _check_availability(db, store.id, [(product.id, it.quantity)])
        chosen, delta = _resolve_modifiers(db, product, it.modifier_ids)
        unit = (product.price + delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line = (unit * it.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += line
        resolved.append((product, it, chosen, unit, line))

    if subtotal < min_order:
        raise DomainError(
            "below_min_order",
            f"Pedido mínimo de {min_order}.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    address = payload.address or {}
    customer = _upsert_customer(db, tid, payload.customer_name, payload.customer_phone, address)
    total = (subtotal + delivery_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if payload.scheduled_time:
        expected = payload.scheduled_time
    elif eta:
        expected = datetime.now(UTC) + timedelta(minutes=eta)
    else:
        expected = None
    order = Order(
        tenant_id=tid, store_id=store.id, customer_id=customer.id, code=_gen_code(db, store.id),
        status="received", channel="own_pwa", fulfillment_type=payload.fulfillment_type,
        subtotal=subtotal, delivery_fee=delivery_fee, total=total, notes=payload.notes,
        expected_time=expected,
    )
    db.add(order)
    db.flush()
    for product, it, chosen, unit, line in resolved:
        db.add(OrderItem(
            tenant_id=tid, order_id=order.id, product_id=product.id, quantity=it.quantity,
            unit_price=unit, total_price=line, notes=it.notes,
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
            recipe_snapshot=_snapshot(db, product.id),
        ))
    db.add(OrderEvent(
        tenant_id=tid, order_id=order.id, event_type="order.created",
        from_status=None, to_status="received",
    ))
    db.add(OrderEvent(
        tenant_id=tid, order_id=order.id, event_type="order.confirmed",
        from_status="received", to_status="received",
    ))
    db.add(OutboxEvent(
        tenant_id=tid,
        event_type="order.confirmed",
        payload={"order_id": str(order.id)},
        idempotency_key=f"order.confirmed:{order.id}",
    ))
    db.add(Payment(
        tenant_id=tid, order_id=order.id, provider="cash", method="cash", amount=total,
        status="pending", idempotency_key=f"order.public:{payload.idempotency_key}",
    ))
    db.commit()
    # Dispara baixa de estoque via outbox (síncrono para garantir consistência)
    from app.modules.orders.outbox import drain_outbox
    drain_outbox(tid)
    return order


def confirm_public_order(
    db: Session, tenant: Tenant, store: Store, payload: PublicOrderConfirm
) -> Order:
    """Confirma um pedido público (para pedidos agendados ou confirmação manual)."""
    existing = db.scalar(
        select(Payment).where(
            Payment.idempotency_key == f"order.public:{payload.idempotency_key}"
        )
    )
    if existing is None:
        raise DomainError(
            "not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND
        )
    order = db.get(Order, existing.order_id)
    if order is None:
        raise DomainError(
            "not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND
        )
    if order.status not in ("received", "confirmed_pending_stock"):
        raise DomainError(
            "invalid_state", "Pedido não pode ser confirmado nesse estado.",
            status.HTTP_409_CONFLICT,
        )
    # Re-valida disponibilidade de estoque
    from app.modules.orders.service import availability_ok
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    if not availability_ok(db, store.id, [(i.product_id, i.quantity) for i in items]):
        order.status = "confirmed_pending_stock"
    else:
        order.status = "confirmed"
    db.add(OrderEvent(
        tenant_id=tenant.id, order_id=order.id, event_type="status.changed",
        from_status="received", to_status=order.status,
    ))
    db.add(OutboxEvent(
        tenant_id=tenant.id,
        event_type="order.confirmed",
        payload={"order_id": str(order.id)},
        idempotency_key=f"order.confirmed:{order.id}",
    ))
    db.commit()
    from app.modules.orders.outbox import drain_outbox
    drain_outbox(order.tenant_id)
    return order


def _eta_minutes(order: Order) -> int | None:
    if order.expected_time is None:
        return None
    delta = order.expected_time - datetime.now(UTC)
    return max(0, math.ceil(delta.total_seconds() / 60))


def public_order_out(db: Session, order: Order) -> PublicOrderOut:
    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id)
    ).all()
    out_items = []
    for it in items:
        product = db.get(Product, it.product_id)
        out_items.append(PublicOrderItemOut(
            product_name=product.name if product else "",
            quantity=it.quantity, unit_price=it.unit_price, total_price=it.total_price,
            modifiers=it.modifiers or [],
        ))
    return PublicOrderOut(
        code=order.code, status=order.status, fulfillment_type=order.fulfillment_type,
        subtotal=order.subtotal, delivery_fee=order.delivery_fee, total=order.total,
        eta_minutes=_eta_minutes(order), created_at=order.created_at, items=out_items,
    )
