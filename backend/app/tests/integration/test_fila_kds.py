from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import SessionLocal
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
    db = SessionLocal()
    try:
        db.execute(text("UPDATE users SET role = :r WHERE email = :e"),
                   {"r": role, "e": f"{slug}@x.com"})
        db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login", json={
        "tenant_slug": slug, "email": f"{slug}@x.com", "password": "senha-segura"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _order(slug, h, name) -> str:
    ing = client.post("/api/v1/insumos", headers=h, json={
        "name": f"ing-{name}",
        "base_unit_symbol": "kg",
        "average_cost": "5.00",
        "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post("/api/v1/produtos", headers=h, json={
        "name": name, "price": "10.00"}).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}]})
    return client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": prod, "quantity": 3}]}).json()["id"]


def test_fila_lista_apenas_em_producao_e_traz_itens() -> None:
    slug = _register("kds-a")
    h = _login(slug, "owner")
    o_conf = _order(slug, h, "Hamburguer")
    client.post(f"/api/v1/pedidos/{o_conf}/confirmar", headers=h)
    o_recv = _order(slug, h, "Pizza")  # fica em received — não entra na fila

    kitchen = _login(slug, "kitchen")
    resp = client.get("/api/v1/cozinha/fila", headers=kitchen)
    assert resp.status_code == 200, resp.text
    codes = [o["order_id"] for o in resp.json()]
    assert o_conf in codes and o_recv not in codes
    row = next(o for o in resp.json() if o["order_id"] == o_conf)
    assert row["items"][0]["product_name"] == "Hamburguer"
    assert row["items"][0]["quantity"] == 3
    assert row["elapsed_minutes"] >= 0


def test_fila_fifo() -> None:
    slug = _register("kds-fifo")
    h = _login(slug, "owner")
    first = _order(slug, h, "A")
    second = _order(slug, h, "B")
    for oid in (first, second):
        client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=h)
    kitchen = _login(slug, "kitchen")
    ids = [o["order_id"] for o in client.get("/api/v1/cozinha/fila", headers=kitchen).json()]
    assert ids.index(first) < ids.index(second)


def test_fila_isola_tenant() -> None:
    slug_a = _register("kds-ta")
    ha = _login(slug_a, "owner")
    oa = _order(slug_a, ha, "Hamburguer")
    client.post(f"/api/v1/pedidos/{oa}/confirmar", headers=ha)

    slug_b = _register("kds-tb")
    hb = _login(slug_b, "kitchen")
    codes = [o["order_id"] for o in client.get("/api/v1/cozinha/fila", headers=hb).json()]
    assert oa not in codes


def test_fila_rbac_buyer_403() -> None:
    slug = _register("kds-rbac")
    buyer = _login(slug, "buyer")
    assert client.get("/api/v1/cozinha/fila", headers=buyer).status_code == 403