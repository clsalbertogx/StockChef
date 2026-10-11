from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import current_actor, get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.models import Ingredient, StockLevel, Supplier
from app.modules.catalog.service import default_store
from app.modules.inventory.service import apply_movement
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
)
from app.modules.purchasing.schemas import (
    GoodsReceiptIn,
    PurchaseOrderCreate,
    PurchaseOrderItemOut,
    PurchaseOrderOut,
    SupplierCreate,
    SupplierOut,
    SupplierUpdate,
)
from app.modules.purchasing.service import purchase_suggestion

router = APIRouter(tags=["compras"])


def _tenant_id(db: Session) -> UUID:
    return UUID(str(db.info["tenant_id"]))


@router.post(
    "/fornecedores",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("owner", "manager"))],
)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> SupplierOut:
    tid = _tenant_id(db)
    supplier = Supplier(
        tenant_id=tid,
        name=payload.name,
        document=payload.document,
        contact_name=payload.contact_name,
        email=payload.email,
        phone=payload.phone,
        lead_time_days=payload.lead_time_days,
        minimum_order_value=payload.minimum_order_value,
        status="active",
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return SupplierOut.model_validate(supplier, from_attributes=True)


@router.get("/fornecedores")
def list_suppliers(db: Session = Depends(get_tenant_db)) -> list[SupplierOut]:  # noqa: B008
    tid = _tenant_id(db)
    rows = db.scalars(select(Supplier).where(
        Supplier.tenant_id == tid
    ).order_by(Supplier.name)).all()
    return [SupplierOut.model_validate(s, from_attributes=True) for s in rows]


@router.get("/fornecedores/{supplier_id}")
def get_supplier(supplier_id: UUID, db: Session = Depends(get_tenant_db)) -> SupplierOut:  # noqa: B008
    tid = _tenant_id(db)
    s = db.get(Supplier, supplier_id)
    if s is None or s.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)
    return SupplierOut.model_validate(s, from_attributes=True)


@router.patch(
    "/fornecedores/{supplier_id}",
    dependencies=[Depends(require_roles("owner", "manager"))],
)
def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> SupplierOut:
    tid = _tenant_id(db)
    s = db.get(Supplier, supplier_id)
    if s is None or s.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(s, field, value)
    db.commit()
    db.refresh(s)
    return SupplierOut.model_validate(s, from_attributes=True)


@router.delete(
    "/fornecedores/{supplier_id}",
    dependencies=[Depends(require_roles("owner", "manager"))],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_supplier(
    supplier_id: UUID, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> None:
    tid = _tenant_id(db)
    s = db.get(Supplier, supplier_id)
    if s is None or s.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)
    db.delete(s)
    db.commit()


@router.get("/compras/sugestao")
def compras_sugestao(
    dias: int = 14,
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(current_actor),  # noqa: B008
) -> list[dict]:
    tid = actor.tenant_id
    store_id = default_store(db, tid).id
    return purchase_suggestion(db, tid, store_id, days=dias)


@router.post("/compras", status_code=status.HTTP_201_CREATED)
def create_po(
    payload: PurchaseOrderCreate,
    actor: Actor = Depends(require_roles("owner", "manager", "buyer")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> PurchaseOrderOut:
    tid = _tenant_id(db)
    sup = db.get(Supplier, payload.supplier_id)
    if sup is None or sup.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)
    store_id = default_store(db, tid).id
    po = PurchaseOrder(
        tenant_id=tid,
        store_id=store_id,
        supplier_id=sup.id,
        status="draft",
        expected_date=payload.expected_date,
        created_by=actor.id,
    )
    db.add(po)
    db.flush()
    total = Decimal("0")
    for it in payload.items:
        ing = db.get(Ingredient, it.ingredient_id)
        if ing is None or ing.tenant_id != tid:
            raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
        ui = ing.base_unit_id
        db.add(
            PurchaseOrderItem(
                tenant_id=tid,
                purchase_order_id=po.id,
                ingredient_id=ing.id,
                quantity=it.quantity,
                unit_id=ui,
                unit_cost=it.unit_cost,
            )
        )
        total += it.quantity * it.unit_cost
    po.total_amount = total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    db.commit()
    return _po_out(db, po)


@router.get("/compras")
def list_pos(
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(current_actor),  # noqa: B008
) -> list[PurchaseOrderOut]:
    tid = actor.tenant_id
    rows = db.scalars(
        select(PurchaseOrder)
        .where(PurchaseOrder.tenant_id == tid)
        .order_by(PurchaseOrder.created_at.desc())
    ).all()
    return [_po_out(db, po) for po in rows]


@router.get("/compras/{po_id}")
def get_po(
    po_id: UUID,
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(current_actor),  # noqa: B008
) -> PurchaseOrderOut:
    tid = actor.tenant_id
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.tenant_id != tid:
        raise DomainError(
            "not_found", "Pedido de compra não encontrado.", status.HTTP_404_NOT_FOUND
        )
    return _po_out(db, po)


@router.post("/compras/{po_id}/aprovar")
def approve_po(
    po_id: UUID,
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> PurchaseOrderOut:
    tid = actor.tenant_id
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.tenant_id != tid:
        raise DomainError(
            "not_found", "Pedido de compra não encontrado.", status.HTTP_404_NOT_FOUND
        )
    if po.status != "draft":
        raise DomainError(
            "invalid_state", "Pedido não está em rascunho.", status.HTTP_409_CONFLICT
        )
    po.status = "sent"
    po.approved_by = actor.id
    db.commit()
    return _po_out(db, po)


@router.post("/compras/{po_id}/recebimento")
def receive_po(
    po_id: UUID,
    payload: GoodsReceiptIn,
    actor: Actor = Depends(require_roles("owner", "manager", "buyer")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> PurchaseOrderOut:
    tid = _tenant_id(db)
    po = db.scalar(
        select(PurchaseOrder).where(PurchaseOrder.id == po_id).with_for_update()
    )
    if po is None or po.tenant_id != tid:
        raise DomainError(
            "not_found", "Pedido de compra não encontrado.", status.HTTP_404_NOT_FOUND
        )
    if po.status not in ("sent", "partially_received"):
        raise DomainError(
            "invalid_state", "Pedido não pode ser recebido.", status.HTTP_409_CONFLICT
        )

    po_items = {
        i.id: i
        for i in db.scalars(
            select(PurchaseOrderItem).where(
                PurchaseOrderItem.purchase_order_id == po.id
            )
        ).all()
    }
    receipt = GoodsReceipt(
        tenant_id=tid,
        purchase_order_id=po.id,
        supplier_id=po.supplier_id,
        received_by=actor.id,
        invoice_number=payload.invoice_number,
        notes=payload.notes,
    )
    db.add(receipt)
    db.flush()

    for it in payload.items:
        po_item = po_items.get(it.purchase_order_item_id)
        if po_item is None:
            raise DomainError(
                "not_found", "Item do pedido não encontrado.", status.HTTP_404_NOT_FOUND
            )
        if it.received_quantity > po_item.quantity - po_item.received_quantity:
            raise DomainError(
                "invalid_state", "Quantidade excede o pendente.", status.HTTP_409_CONFLICT
            )
        ing = db.get(Ingredient, po_item.ingredient_id)
        assert ing is not None
        sl = db.scalar(
            select(StockLevel)
            .where(
                StockLevel.store_id == po.store_id,
                StockLevel.ingredient_id == po_item.ingredient_id,
            )
            .with_for_update()
        )
        if sl is None:
            sl = StockLevel(
                tenant_id=tid,
                store_id=po.store_id,
                ingredient_id=po_item.ingredient_id,
                quantity=Decimal("0"),
                average_cost=ing.average_cost,
            )
            db.add(sl)
            db.flush()
        db.add(
            GoodsReceiptItem(
                tenant_id=tid,
                goods_receipt_id=receipt.id,
                purchase_order_item_id=po_item.id,
                ingredient_id=po_item.ingredient_id,
                quantity=it.received_quantity,
                unit_cost=it.unit_cost,
            )
        )
        apply_movement(
            db,
            tenant_id=tid,
            store_id=po.store_id,
            ingredient_id=po_item.ingredient_id,
            type_="purchase",
            quantity=it.received_quantity,
            unit_cost=it.unit_cost,
            reference_type="goods_receipt",
            reference_id=receipt.id,
            idempotency_key=f"receipt:{receipt.id}:{po_item.id}",
            user_id=actor.id,
        )
        ing.average_cost = sl.average_cost
        po_item.received_quantity += it.received_quantity

    pending = any(
        (i.quantity - i.received_quantity) > 0 for i in po_items.values()
    )
    po.status = "received" if not pending else "partially_received"
    db.commit()
    return _po_out(db, po)


@router.post("/compras/{po_id}/cancelar")
def cancel_po(
    po_id: UUID,
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> PurchaseOrderOut:
    tid = actor.tenant_id
    po = db.get(PurchaseOrder, po_id)
    if po is None or po.tenant_id != tid:
        raise DomainError(
            "not_found", "Pedido de compra não encontrado.", status.HTTP_404_NOT_FOUND
        )
    if po.status == "canceled":
        return _po_out(db, po)
    if po.status == "received":
        raise DomainError(
            "invalid_state", "Pedido não pode ser cancelado.", status.HTTP_409_CONFLICT
        )
    po.status = "canceled"
    db.commit()
    return _po_out(db, po)


def _po_out(db: Session, po: PurchaseOrder) -> PurchaseOrderOut:
    items = db.scalars(
        select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == po.id)
    ).all()
    return PurchaseOrderOut(
        id=po.id,
        supplier_id=po.supplier_id,
        status=po.status,
        expected_date=po.expected_date,
        total_amount=po.total_amount,
        approved_by=po.approved_by,
        created_at=po.created_at,
        items=[PurchaseOrderItemOut.model_validate(i) for i in items],
    )

