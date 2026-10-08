from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.modules.catalog.models import Supplier
from app.modules.purchasing.schemas import SupplierCreate, SupplierOut, SupplierUpdate

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
    return SupplierOut.model_validate(supplier)


@router.get("/fornecedores")
def list_suppliers(db: Session = Depends(get_tenant_db)) -> list[SupplierOut]:  # noqa: B008
    tid = _tenant_id(db)
    rows = db.scalars(select(Supplier).where(
        Supplier.tenant_id == tid
    ).order_by(Supplier.name)).all()
    return [SupplierOut.model_validate(s) for s in rows]


@router.get("/fornecedores/{supplier_id}")
def get_supplier(supplier_id: UUID, db: Session = Depends(get_tenant_db)) -> SupplierOut:  # noqa: B008
    tid = _tenant_id(db)
    s = db.get(Supplier, supplier_id)
    if s is None or s.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)
    return SupplierOut.model_validate(s)


@router.patch("/fornecedores/{supplier_id}")
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
    return SupplierOut.model_validate(s)


@router.delete("/fornecedores/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_supplier(
    supplier_id: UUID, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> None:
    tid = _tenant_id(db)
    s = db.get(Supplier, supplier_id)
    if s is None or s.tenant_id != tid:
        raise DomainError("not_found", "Fornecedor não encontrado.", status.HTTP_404_NOT_FOUND)
    db.delete(s)
    db.commit()
