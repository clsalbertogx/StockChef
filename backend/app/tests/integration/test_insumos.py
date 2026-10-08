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


def test_create_duplicate_name_409() -> None:
    h = _auth_headers("dup-ins")
    client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "Tomate", "base_unit_symbol": "kg", "average_cost": "5"},
    )
    resp = client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "Tomate", "base_unit_symbol": "kg", "average_cost": "6"},
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "insumo_exists"


def test_patch_duplicate_name_409() -> None:
    h = _auth_headers("dup-patch")
    client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "Cenoura", "base_unit_symbol": "kg", "average_cost": "5"},
    )
    r2 = client.post(
        "/api/v1/insumos", headers=h,
        json={"name": "Berinjela", "base_unit_symbol": "kg", "average_cost": "7"},
    )
    resp = client.patch(f"/api/v1/insumos/{r2.json()['id']}", headers=h, json={"name": "Cenoura"})
    assert resp.status_code == 409
    assert resp.json()["code"] == "insumo_exists"


def test_get_insumo_by_id_200_and_404() -> None:
    h = _auth_headers("get-ins")
    created = client.post(
        "/api/v1/insumos", headers=h,
        json={
            "name": "Peito", "base_unit_symbol": "kg",
            "average_cost": "12.50", "initial_stock": "1",
        },
    ).json()
    resp = client.get(f"/api/v1/insumos/{created['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["average_cost"] == "12.50"

    import uuid

    missing = client.get(f"/api/v1/insumos/{uuid.uuid4()}", headers=h)
    assert missing.status_code == 404
    assert missing.json()["code"] == "not_found"


def test_get_list_decimals_are_consistent() -> None:
    h = _auth_headers("dec-im")
    client.post(
        "/api/v1/insumos", headers=h,
        json={
            "name": "Mussarela", "base_unit_symbol": "kg",
            "average_cost": "45.00", "initial_stock": "3",
        },
    )
    body = client.get("/api/v1/insumos", headers=h).json()[0]
    assert body["average_cost"] == "45.00"
    assert body["stock_total"] == "3.00"
