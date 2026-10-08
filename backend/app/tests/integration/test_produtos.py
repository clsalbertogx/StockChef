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


def test_create_product_duplicate_name_409() -> None:
    h = _setup("dup-prod")
    client.post("/api/v1/produtos", headers=h, json={"name": "X", "price": "10"})
    resp = client.post("/api/v1/produtos", headers=h, json={"name": "X", "price": "12"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "product_exists"


def test_create_product_foreign_store_404() -> None:
    from sqlalchemy import text

    from app.core.db import SessionLocal, set_tenant

    from app.modules.identity.models import Tenant

    h_a = _setup("prod-a")
    _setup("prod-b")

    def _tid(slug: str) -> str:
        s = SessionLocal()
        try:
            return str(s.scalar(
                text("SELECT id FROM tenants WHERE slug = :s"), {"s": slug}
            ))
        finally:
            s.close()

    db = SessionLocal()
    try:
        set_tenant(db, _tid("prod-b"))
        store_b = db.execute(text("SELECT id FROM stores")).scalar()
    finally:
        db.close()
    resp = client.post(
        "/api/v1/produtos", headers=h_a,
        json={"name": "Vazado", "price": "10", "store_id": str(store_b)},
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "store_not_found"


def test_get_product_by_id_200_and_404() -> None:
    import uuid

    h = _setup("get-prod")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "Z", "price": "9"}).json()["id"]
    resp = client.get(f"/api/v1/produtos/{pid}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Z"
    missing = client.get(f"/api/v1/produtos/{uuid.uuid4()}", headers=h)
    assert missing.status_code == 404


def test_margem_endpoint() -> None:
    h = _setup("margem")
    queijo = _insumo(h, "Queijo", "45.00", "kg")
    pid = client.post(
        "/api/v1/produtos", headers=h, json={"name": "M", "price": "20.00"}
    ).json()["id"]
    client.post(
        f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h,
        json={"items": [{"ingredient_id": queijo, "quantity": "0.030"}]},
    )
    resp = client.get(f"/api/v1/produtos/{pid}/margem", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cost"] == "1.35"
    assert body["margin_value"] == "18.65"
    assert body["margin_percent"] == "93.25"


def test_ficha_empty_items_422() -> None:
    h = _setup("vazia")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "V", "price": "10"}).json()["id"]
    resp = client.post(
        f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": []}
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"
