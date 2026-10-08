from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _insumo(h: dict[str, str], name: str, avg: str, unit: str = "kg", stock: str = "0") -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": unit, "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_create_product_and_recipe_cost() -> None:
    h = _setup("burguer")
    queijo = _insumo(h, "Queijo cheddar", "45.00", "kg", "3.00")
    pao = _insumo(h, "Pão brioche", "1.00", "un", "50")
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "20.00"})
    assert p.status_code == 201, p.text
    pid = p.json()["id"]

    resp = client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={
        "items": [
            {"ingredient_id": queijo, "quantity": "0.030"},
            {"ingredient_id": pao, "quantity": "2"},
        ],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["total_cost"] == "3.35"

    ficha = client.get(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h).json()
    queijo_item = next(i for i in ficha["items"] if i["name"] == "Queijo cheddar")
    assert queijo_item["cost"] == "1.35"


def test_ficha_replaces_items() -> None:
    h = _setup("burger2")
    queijo = _insumo(h, "Queijo", "45.00", "kg")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "X", "price": "10"}).json()["id"]
    body1 = {"items": [{"ingredient_id": queijo, "quantity": "0.020"}]}
    client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json=body1)
    body2 = {"items": [{"ingredient_id": queijo, "quantity": "0.040"}]}
    resp = client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json=body2)
    assert len(resp.json()["items"]) == 1
    assert resp.json()["total_cost"] == "1.80"


def test_ficha_unknown_ingredient_404() -> None:
    import uuid
    h = _setup("burger3")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "Y", "price": "10"}).json()["id"]
    item = {"ingredient_id": str(uuid.uuid4()), "quantity": "1"}
    resp = client.post(
        f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": [item]}
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
