from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import SessionLocal, set_tenant
from app.main import app
from app.modules.catalog.models import StockLevel
from app.modules.identity.models import Tenant

client = TestClient(app)


def _setup(slug: str) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    # devolve o SLUG (não o tenant_id): os corpos de teste (verbatim) passam essa
    # string de volta para _tenant_id(...); repassar o uuid faria a consulta retornar None
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, slug


def _tenant_id(slug: str) -> str:
    db = SessionLocal()
    try:
        return str(db.scalar(select(Tenant.id).where(Tenant.slug == slug)))
    finally:
        db.close()


def _ingredient(h, name, avg, stock) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg",
        "average_cost": avg, "initial_stock": stock,
    })
    return r.json()["id"]


def _xburger(h, queijo: str) -> str:
    p = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "20.00"}
    ).json()["id"]
    client.post(
        f"/api/v1/produtos/{p}/ficha-tecnica", headers=h,
        json={"items": [{"ingredient_id": queijo, "quantity": "0.030"}]},
    )
    return p


def _stock(ingredient_id: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tenant_id(slug))
        qty = db.scalar(
            select(StockLevel.quantity).where(StockLevel.ingredient_id == ingredient_id)
        )
        assert qty is not None
        return str(Decimal(qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    finally:
        db.close()


def _movements(ingredient_id: str, slug: str) -> Sequence[tuple[Any, ...]]:
    db = SessionLocal()
    try:
        set_tenant(db, _tenant_id(slug))
        sql = (
            "SELECT type, quantity FROM stock_movements"
            " WHERE ingredient_id = :i ORDER BY created_at"
        )
        return db.execute(text(sql), {"i": ingredient_id}).all()
    finally:
        db.close()


def test_confirm_gherkin_beixa_automatica() -> None:
    h, slug = _setup("baixa")
    queijo = _ingredient(h, "Queijo cheddar", "45.00", "3.00")
    pid = _xburger(h, queijo)
    order = client.post(
        "/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 2}]}
    ).json()

    resp = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "confirmed"

    assert _stock(queijo, slug) == "2.94"  # 3.00 − 2 × 0.030
    mov = _movements(queijo, slug)
    assert len(mov) == 1
    assert mov[0][0] == "sale"


def test_confirm_is_idempotent() -> None:
    h, slug = _setup("idemp")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post(
        "/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    again = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert again.status_code == 200
    assert _stock(queijo, slug) == "0.97"          # baixa aplicada UMA vez
    assert len(_movements(queijo, slug)) == 1


def test_insufficient_becomes_confirmed_pending_stock() -> None:
    # Contradição do brief: com estoque 0.020 a criação do pedido já 422 (contrato T7,
    # test_pedidos.py::test_create_order_insufficient_stock_422, congelado). Construímos a
    # shortage no momento da confirmação (race real coberta por §6.3 "confirmar não bloqueia
    # venda"): estoque suficiente ao criar, esgotado via UPDATE direto antes do confirmar.
    h, slug = _setup("pend")
    queijo = _ingredient(h, "Queijo", "45.00", "0.050")
    pid = _xburger(h, queijo)
    order = client.post(
        "/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    db = SessionLocal()
    try:
        set_tenant(db, _tenant_id(slug))
        db.execute(text(
            "UPDATE stock_levels SET quantity = :q WHERE ingredient_id = :i"
        ), {"q": "0.020", "i": queijo})
        db.commit()
    finally:
        db.close()
    resp = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed_pending_stock"
    assert _stock(queijo, slug) == "0.02"          # nada foi baixado
    assert len(_movements(queijo, slug)) == 0


def test_outbox_reprocessed_is_noop() -> None:
    h, slug = _setup("reproc")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post(
        "/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert _stock(queijo, slug) == "0.97"

    tenant_id = _tenant_id(slug)
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)  # outbox_events tem RLS — sessão precisa do tenant ativo
        row = db.execute(
            text("SELECT id FROM outbox_events WHERE payload->>'order_id' = :oid"),
            {"oid": order["id"]},
        ).one()
        db.execute(
            text("UPDATE outbox_events SET status = 'pending' WHERE id = :id"),
            {"id": row[0]},
        )
        db.commit()
    finally:
        db.close()

    from uuid import UUID

    from app.modules.orders.outbox import drain_outbox

    drain_outbox(UUID(tenant_id))

    assert _stock(queijo, slug) == "0.97"          # reprocessar não baixa de novo
    assert len(_movements(queijo, slug)) == 1


def test_events_expose_outbox_status() -> None:
    h, _ = _setup("eventos")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post(
        "/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}
    ).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    resp = client.get(f"/api/v1/pedidos/{order['id']}/eventos", headers=h)
    assert resp.status_code == 200
    assert any(e["outbox_status"] == "processed" for e in resp.json()["events"])
