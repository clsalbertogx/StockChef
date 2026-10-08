from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_headers(slug: str, email: str = "dono@x.com") -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": email,
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_insumo_with_initial_stock() -> None:
    h = _auth_headers("queijaria")
    resp = client.post("/api/v1/insumos", headers=h, json={
        "name": "Queijo cheddar", "base_unit_symbol": "kg",
        "average_cost": "45.00", "initial_stock": "3.00",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Queijo cheddar"
    assert body["base_unit"]["symbol"] == "kg"
    assert body["average_cost"] == "45.00"
    assert body["stock_total"] == "3.00"


def test_unit_is_reused_per_tenant() -> None:
    h = _auth_headers("unidades")
    r1 = client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "A", "base_unit_symbol": "kg", "average_cost": "1"},
    )
    r2 = client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "B", "base_unit_symbol": "kg", "average_cost": "2"},
    )
    assert r1.json()["base_unit"]["id"] == r2.json()["base_unit"]["id"]


def test_patch_average_cost_propagates() -> None:
    h = _auth_headers("precos")
    r = client.post(
        "/api/v1/insumos", headers=h, json={
            "name": "Pão", "base_unit_symbol": "un", "average_cost": "1.00", "initial_stock": "10",
        },
    )
    insumo_id = r.json()["id"]
    resp = client.patch(f"/api/v1/insumos/{insumo_id}", headers=h, json={"average_cost": "1.50"})
    assert resp.status_code == 200
    assert resp.json()["average_cost"] == "1.50"


def test_list_is_isolated_per_tenant() -> None:
    h_a = _auth_headers("ins-a")
    h_b = _auth_headers("ins-b", email="b@x.com")
    client.post(
        "/api/v1/insumos", headers=h_a,
        json={"name": "Alface", "base_unit_symbol": "un", "average_cost": "0.5"},
    )
    lista = client.get("/api/v1/insumos", headers=h_b).json()
    assert lista == []
