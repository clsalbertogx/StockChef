from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(slug: str) -> str:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return slug


def _login(slug: str, role: str) -> dict[str, str]:
    from sqlalchemy import text

    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE users SET role = :r WHERE email = :e"),
            {"r": role, "e": f"{slug}@x.com"},
        )
        db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login", json={
        "tenant_slug": slug, "email": f"{slug}@x.com", "password": "senha-segura",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _order(slug: str, h_owner: dict[str, str]) -> str:
    ing = client.post("/api/v1/insumos", headers=h_owner, json={
        "name": "Pao", "base_unit_symbol": "kg", "average_cost": "5.00", "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post(
        "/api/v1/produtos", headers=h_owner, json={"name": "X", "price": "10.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h_owner, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}],
    })
    return client.post(
        "/api/v1/pedidos", headers=h_owner, json={"items": [{"product_id": prod, "quantity": 1}]}
    ).json()["id"]


def _patch(h: dict[str, str], oid: str, to: str):
    return client.patch(f"/api/v1/pedidos/{oid}/status", headers=h, json={"status": to})


def test_received_nao_vai_para_preparing_409() -> None:
    slug = _register("st-recv")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    r = _patch(owner, oid, "preparing")
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_state"


def test_fluxo_completo_confirma_prepara_pronto_entrega_conclui() -> None:
    slug = _register("st-fluxo")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    assert client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner).status_code == 200

    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").json()["status"] == "preparing"
    assert _patch(kitchen, oid, "ready").json()["status"] == "ready"

    cashier = _login(slug, "cashier")
    assert _patch(cashier, oid, "delivered").json()["status"] == "delivered"
    assert _patch(owner, oid, "completed").json()["status"] == "completed"

    events = client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"]
    changed = [e for e in events if e["event_type"] == "status.changed"]
    assert [e["to_status"] for e in changed] == [
        "confirmed", "preparing", "ready", "delivered", "completed",
    ]


def test_confirmed_pending_stock_pode_preparar() -> None:
    from sqlalchemy import select, text

    from app.core.db import SessionLocal, set_tenant
    from app.modules.identity.models import Tenant

    slug = _register("st-pend")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    db = SessionLocal()
    try:
        set_tenant(db, db.scalar(select(Tenant.id).where(Tenant.slug == slug)))
        db.execute(
            text("UPDATE orders SET status = 'confirmed_pending_stock' WHERE id = :i"),
            {"i": oid},
        )
        db.commit()
    finally:
        db.close()
    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").status_code == 200


def test_ready_nao_volta_para_confirmed_409() -> None:
    slug = _register("st-ready")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    kitchen = _login(slug, "kitchen")
    _patch(kitchen, oid, "preparing")
    _patch(kitchen, oid, "ready")
    r = _patch(kitchen, oid, "confirmed")
    assert r.status_code == 409


def test_noop_mesmo_status_nao_grava_evento() -> None:
    slug = _register("st-noop")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    before = len(client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"])
    r = _patch(owner, oid, "confirmed")
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    after = len(client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"])
    assert after == before


def test_rbac_transicoes() -> None:
    slug = _register("st-rbac")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)

    cashier = _login(slug, "cashier")
    assert _patch(cashier, oid, "preparing").status_code == 403  # cashier não prepara

    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").status_code == 200
    _patch(kitchen, oid, "ready")
    assert _patch(kitchen, oid, "delivered").status_code == 403  # kitchen não entrega


def test_ready_pode_concluir_direto() -> None:
    slug = _register("st-ready-done")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    kitchen = _login(slug, "kitchen")
    _patch(kitchen, oid, "preparing")
    _patch(kitchen, oid, "ready")
    assert _patch(owner, oid, "completed").status_code == 200
    assert _patch(owner, oid, "completed").json()["status"] == "completed"


def test_delivered_para_completed_so_owner_manager() -> None:
    slug = _register("st-deliv-done")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    kitchen = _login(slug, "kitchen")
    _patch(kitchen, oid, "preparing")
    _patch(kitchen, oid, "ready")
    cashier = _login(slug, "cashier")
    assert _patch(cashier, oid, "delivered").status_code == 200
    assert _patch(cashier, oid, "completed").status_code == 403  # cashier não conclui
    assert _patch(owner, oid, "completed").status_code == 200
