from fastapi.testclient import TestClient
from httpx import Response

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ingredient(h, name, avg, stock) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg",
        "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(h, name, price, ficha: list[tuple[str, str]]) -> str:
    r = client.post("/api/v1/produtos", headers=h, json={"name": name, "price": price})
    pid = r.json()["id"]
    client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": i, "quantity": q} for i, q in ficha],
    })
    return pid


def _order(h, product_id: str, qty: int) -> Response:
    return client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": product_id, "quantity": qty}],
    })


def test_create_order_with_stock() -> None:
    h = _setup("pedido1")
    queijo = _ingredient(h, "Queijo", "45.00", "3.00")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    resp = _order(h, pid, 2)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "received"
    assert body["total"] == "40.00"
    assert body["code"].startswith("SC-")
    assert len(body["order_items"]) == 1


def test_create_order_insufficient_stock_422() -> None:
    h = _setup("pedido2")
    queijo = _ingredient(h, "Queijo", "45.00", "0.050")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    resp = _order(h, pid, 2)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "insufficient_stock"
    assert body["missing"][0]["required"] == "0.0600"


def test_create_order_recipe_missing_422() -> None:
    h = _setup("pedido3")
    r = client.post("/api/v1/produtos", headers=h, json={"name": "Sem Ficha", "price": "10"})
    pid = r.json()["id"]
    resp = _order(h, pid, 1)
    assert resp.status_code == 422
    assert resp.json()["code"] == "recipe_missing"


def test_list_orders_scoped() -> None:
    h = _setup("pedido4")
    queijo = _ingredient(h, "Queijo", "45.00", "3.00")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    _order(h, pid, 1)
    lista = client.get("/api/v1/pedidos", headers=h)
    assert lista.status_code == 200
    assert len(lista.json()) == 1
