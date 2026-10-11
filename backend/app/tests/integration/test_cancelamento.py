from decimal import ROUND_HALF_UP, Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.core.db import SessionLocal, set_tenant
from app.main import app
from app.modules.catalog.models import StockLevel
from app.modules.identity.models import Tenant
from uuid import UUID

client = TestClient(app)

def _setup(slug: str) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, slug

def _tid(slug: str) -> str:
    db = SessionLocal()
    try:
        return str(db.scalar(select(Tenant.id).where(Tenant.slug == slug)))
    finally:
        db.close()

def _ing(h, name, avg, stock) -> str:
    return client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock,
    }).json()["id"]

def _prod(h, ing) -> str:
    p = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X", "price": "10.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{p}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.030"}],
    })
    return p

def _stock(ing: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        q = db.scalar(select(StockLevel.quantity).where(StockLevel.ingredient_id == ing))
        assert q is not None
        return str(Decimal(q).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    finally:
        db.close()

def _cost(ing: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        c = db.scalar(select(StockLevel.average_cost).where(StockLevel.ingredient_id == ing))
        assert c is not None
        return str(Decimal(c).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    finally:
        db.close()

def _types(ing: str, slug: str) -> list[str]:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        return [r[0] for r in db.execute(text(
            "SELECT type FROM stock_movements WHERE ingredient_id = :i ORDER BY created_at"
        ), {"i": ing}).all()]
    finally:
        db.close()

def test_cancelar_reverte_estoque_e_preserva_custo_medio() -> None:
    h, slug = _setup("cancela")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 2}]}).json()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)
    assert _stock(ing, slug) == "2.94"
    assert _cost(ing, slug) == "45.00"

    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "cliente desistiu"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert _stock(ing, slug) == "3.00"
    assert _cost(ing, slug) == "45.00"
    assert _types(ing, slug) == ["sale", "reversal"]

    events = client.get(f"/api/v1/pedidos/{o['id']}/eventos", headers=h).json()["events"]
    cancel = next(e for e in events if e["event_type"] == "order.cancelled")
    assert cancel["to_status"] == "cancelled"

def test_cancelar_duas_vezes_e_idempotente() -> None:
    h, slug = _setup("canc-idem")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)
    client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "x"})
    first = _stock(ing, slug)
    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "x"})
    assert r.status_code == 200
    assert _stock(ing, slug) == first
    assert _types(ing, slug) == ["sale", "reversal"]

def test_cancelar_pending_stock_nao_cria_reversao() -> None:
    h, slug = _setup("canc-pend")
    ing = _ing(h, "Queijo", "45.00", "0.05")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        db.execute(text("UPDATE stock_levels SET quantity = 0.02 WHERE ingredient_id = :i"), {"i": ing})
        db.commit()
    finally:
        db.close()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)
    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "sem estoque"})
    assert r.status_code == 200
    assert _types(ing, slug) == []
    assert _stock(ing, slug) == "0.02"

def test_cancelar_delivered_409_e_motivo_obrigatorio() -> None:
    h, slug = _setup("canc-term")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        db.execute(text("UPDATE orders SET status='delivered' WHERE id=:i"), {"i": o["id"]})
        db.commit()
    finally:
        db.close()
    assert client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h,
                       json={"motivo": "x"}).status_code == 409
    o2 = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    assert client.post(f"/api/v1/pedidos/{o2['id']}/cancelar", headers=h,
                       json={"motivo": ""}).status_code == 422
