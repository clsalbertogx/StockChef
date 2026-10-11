from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import SessionLocal, set_tenant
from app.main import app
from app.modules.catalog.models import Ingredient, Store, Supplier, Unit
from app.modules.identity.models import Tenant
from app.modules.inventory.models import InventoryCount, InventoryCountItem, Loss
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
)


@pytest.fixture()
def tenant_id() -> str:
    c = TestClient(app)
    r = c.post("/api/v1/auth/register", json={
        "tenant_name": "modelos", "tenant_slug": "modelos",
        "email": "m@x.com", "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    db = SessionLocal()
    try:
        return str(db.scalar(select(Tenant.id).where(Tenant.slug == "modelos")))
    finally:
        db.close()


def test_models_mapeiam_ddl(tenant_id: str) -> None:
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)
        store = db.scalars(select(Store)).one()
        unit = db.scalars(select(Unit)).first()
        assert unit is not None
        ing = Ingredient(tenant_id=tenant_id, name="Insumo teste", base_unit_id=unit.id,
                         average_cost=Decimal("1"), status="active")
        db.add(ing)
        sup = Supplier(tenant_id=tenant_id, name="Fornecedor teste", status="active")
        db.add(sup)
        db.flush()

        db.add(Loss(tenant_id=tenant_id, store_id=store.id, ingredient_id=ing.id,
                    quantity=Decimal("1"), cost=Decimal("1.00"), reason="damage"))
        db.add(InventoryCount(tenant_id=tenant_id, store_id=store.id))
        db.flush()
        count = db.scalars(select(InventoryCount)).one()
        db.add(InventoryCountItem(tenant_id=tenant_id, inventory_count_id=count.id,
                                  ingredient_id=ing.id, system_quantity=Decimal("1")))
        po = PurchaseOrder(tenant_id=tenant_id, store_id=store.id, supplier_id=sup.id)
        db.add(po)
        db.flush()
        poi = PurchaseOrderItem(tenant_id=tenant_id, purchase_order_id=po.id,
                                ingredient_id=ing.id, quantity=Decimal("1"),
                                unit_id=unit.id, unit_cost=Decimal("1"))
        db.add(poi)
        gr = GoodsReceipt(tenant_id=tenant_id, supplier_id=sup.id)
        db.add(gr)
        db.flush()
        db.add(GoodsReceiptItem(tenant_id=tenant_id, goods_receipt_id=gr.id,
                                purchase_order_item_id=poi.id, ingredient_id=ing.id,
                                quantity=Decimal("1"), unit_cost=Decimal("1")))
        db.commit()

        assert db.scalar(select(Loss).where(Loss.tenant_id == tenant_id)) is not None
        assert db.scalar(select(InventoryCountItem)) is not None
        assert db.scalar(select(PurchaseOrderItem)) is not None
        assert db.scalar(select(GoodsReceiptItem)) is not None
    finally:
        db.close()
