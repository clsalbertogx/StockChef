from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _supplier(h) -> str:
    return client.post("/api/v1/fornecedores", headers=h, json={"name": "Sup"}).json()["id"]


def _insumo(h, name: str, avg: str, stock: str) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _po(h, sup: str, iid: str) -> str:
    r = client.post("/api/v1/compras", headers=h, json={
        "supplier_id": sup,
        "items": [{"ingredient_id": iid, "quantity": "10", "unit_cost": "4"}],
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_recebimento_parcial_aplica_custo_medio() -> None:
    h = _auth("rec")
    sup = _supplier(h)
    iid = _insumo(h, "Arroz", "2.00", "0")
    pid = _po(h, sup, iid)
    client.post(f"/api/v1/compras/{pid}/aprovar", headers=h)
    item_id = client.get(f"/api/v1/compras/{pid}", headers=h).json()["items"][0]["id"]

    r1 = client.post(f"/api/v1/compras/{pid}/recebimento", headers=h, json={
        "items": [{"purchase_order_item_id": item_id, "received_quantity": "4", "unit_cost": "3"}],
    })
    assert r1.status_code == 200, r1.text
    assert r1.json()["status"] == "partially_received"
    ins = client.get(f"/api/v1/insumos/{iid}", headers=h).json()
    assert ins["average_cost"] == "3.00", ins
    assert ins["stock_total"] == "4.00", ins

    r2 = client.post(f"/api/v1/compras/{pid}/recebimento", headers=h, json={
        "items": [{"purchase_order_item_id": item_id, "received_quantity": "6", "unit_cost": "3"}],
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "received"
    assert client.get(f"/api/v1/insumos/{iid}", headers=h).json()["stock_total"] == "10.00"


def test_recebimento_excede_quantidade_409() -> None:
    h = _auth("rec2")
    sup = _supplier(h)
    iid = _insumo(h, "Feijão", "2", "0")
    pid = _po(h, sup, iid)
    client.post(f"/api/v1/compras/{pid}/aprovar", headers=h)
    item_id = client.get(f"/api/v1/compras/{pid}", headers=h).json()["items"][0]["id"]
    ok = client.post(f"/api/v1/compras/{pid}/recebimento", headers=h, json={
        "items": [{"purchase_order_item_id": item_id, "received_quantity": "10", "unit_cost": "2"}],
    })
    assert ok.status_code == 200
    bad = client.post(f"/api/v1/compras/{pid}/recebimento", headers=h, json={
        "items": [{"purchase_order_item_id": item_id, "received_quantity": "1", "unit_cost": "2"}],
    })
    assert bad.status_code == 409
    assert bad.json()["code"] == "invalid_state"
