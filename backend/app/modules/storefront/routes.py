from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.delivery.models import Zone
from app.modules.delivery.service import resolve_zone
from app.modules.identity.models import Tenant
from app.modules.orders.models import Order
from app.modules.storefront import viacep
from app.modules.storefront.deps import get_public_db
from app.modules.storefront.schemas import (
    DeliveryEstimateOut,
    PublicMenuOut,
    PublicOrderConfirm,
    PublicOrderCreate,
    PublicOrderOut,
)
from app.modules.storefront.service import (
    confirm_public_order,
    create_public_order,
    current_store,
    public_menu,
    public_order_out,
)

router = APIRouter(tags=["storefront"])


@router.get("/public/{slug}/cardapio")
def get_cardapio(
    slug: str,
    q: str | None = Query(default=None, max_length=80),
    category_id: UUID | None = None,
    db: Session = Depends(get_public_db),  # noqa: B008
) -> PublicMenuOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None  # resolvido em get_public_db
    store = current_store(db, tid)
    return public_menu(db, tenant, store, q, category_id)


@router.get("/public/{slug}/cep/{cep}")
def get_cep(slug: str, cep: str, db: Session = Depends(get_public_db)) -> dict:  # noqa: B008
    try:
        return viacep.lookup(cep)
    except viacep.ViaCepError as exc:
        if exc.kind == "invalid":
            raise DomainError(
                "cep_invalid", "CEP inválido.", status.HTTP_422_UNPROCESSABLE_ENTITY
            ) from exc
        if exc.kind == "not_found":
            raise DomainError(
                "cep_not_found", "CEP não encontrado.", status.HTTP_404_NOT_FOUND
            ) from exc
        raise DomainError(
            "cep_unavailable",
            "Consulta de CEP indisponível no momento.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


@router.get("/public/{slug}/entrega")
def get_entrega(
    slug: str, cep: str, db: Session = Depends(get_public_db)  # noqa: B008
) -> DeliveryEstimateOut:
    tid = db.info["tenant_id"]
    store = current_store(db, tid)
    zone = resolve_zone(db, store.id, cep)
    if zone is not None:
        return DeliveryEstimateOut(
            covered=True, zone_name=zone.name, delivery_fee=zone.delivery_fee,
            min_order_value=zone.min_order_value, eta_minutes=zone.eta_minutes,
        )
    has_zones = bool(
        db.scalar(select(Zone.id).where(Zone.store_id == store.id, Zone.active.is_(True)))
    )
    return DeliveryEstimateOut(
        covered=not has_zones, zone_name=None, delivery_fee=Decimal("0.00"),
        min_order_value=Decimal("0.00"), eta_minutes=30 if not has_zones else 0,
    )


@router.post("/public/{slug}/pedidos", status_code=status.HTTP_201_CREATED)
def create_pedido(
    slug: str, payload: PublicOrderCreate, db: Session = Depends(get_public_db)  # noqa: B008
) -> PublicOrderOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None
    store = current_store(db, tid)
    order = create_public_order(db, tenant, store, payload)
    return public_order_out(db, order)


@router.post("/public/{slug}/pedidos/confirmar", status_code=status.HTTP_200_OK)
def confirm_pedido(
    slug: str, payload: PublicOrderConfirm, db: Session = Depends(get_public_db)  # noqa: B008
) -> PublicOrderOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None
    store = current_store(db, tid)
    order = confirm_public_order(db, tenant, store, payload)
    return public_order_out(db, order)


@router.get("/public/{slug}/pedidos/{code}")
def get_pedido(
    slug: str, code: str, db: Session = Depends(get_public_db)  # noqa: B008
) -> PublicOrderOut:
    order = db.scalar(select(Order).where(Order.code == code))
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    return public_order_out(db, order)
