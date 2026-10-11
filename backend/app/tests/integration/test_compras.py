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


def _supplier(h, name: str = "Sup") -> str:
    r = client.post("/api/v1/fornecedores", headers=h, json={"name": name, "lead_time_days": 1})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _insumo(h, name: str, avg: str, stock: str = "1") -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_po_draft_aprovar_e_cancelar() -> None:
    h = _auth("po1")
    sup = _supplier(h)
    iid = _insumo(h, "Tomate", "3")
    po = client.post("/api/v1/compras", headers=h, json={
        "supplier_id": sup,
        "items": [{"ingredient_id": iid, "quantity": "10", "unit_cost": "3.20"}],
    })
    assert po.status_code == 201, po.text
    pid = po.json()["id"]
    assert po.json()["status"] == "draft"
    assert po.json()["total_amount"] == "32.00"

    aprova = client.post(f"/api/v1/compras/{pid}/aprovar", headers=h)
    assert aprova.status_code == 200
    assert aprova.json()["status"] == "sent"

    cancela = client.post(f"/api/v1/compras/{pid}/cancelar", headers=h)
    assert cancela.status_code == 200
    assert cancela.json()["status"] == "canceled"


def test_total_usa_round_half_up() -> None:
    h = _auth("po3")
    sup = _supplier(h)
    iid = _insumo(h, "Cebola", "1")
    po = client.post("/api/v1/compras", headers=h, json={
        "supplier_id": sup,
        "items": [{"ingredient_id": iid, "quantity": "0.25", "unit_cost": "0.50"}],
    })
    assert po.status_code == 201, po.text
    assert po.json()["total_amount"] == "0.13"


def test_cancelar_duas_vezes_e_idempotente() -> None:
    h = _auth("po4")
    sup = _supplier(h)
    iid = _insumo(h, "Cenoura", "1")
    pid = client.post("/api/v1/compras", headers=h, json={
        "supplier_id": sup,
        "items": [{"ingredient_id": iid, "quantity": "1", "unit_cost": "1"}],
    }).json()["id"]

    first = client.post(f"/api/v1/compras/{pid}/cancelar", headers=h)
    assert first.status_code == 200
    assert first.json()["status"] == "canceled"

    second = client.post(f"/api/v1/compras/{pid}/cancelar", headers=h)
    assert second.status_code == 200
    assert second.json()["status"] == "canceled"


def test_aprovar_po_em_sent_409() -> None:
    h = _auth("po2")
    sup = _supplier(h)
    iid = _insumo(h, "Alface", "2")
    pid = client.post("/api/v1/compras", headers=h, json={
        "supplier_id": sup,
        "items": [{"ingredient_id": iid, "quantity": "5", "unit_cost": "2"}],
    }).json()["id"]
    client.post(f"/api/v1/compras/{pid}/aprovar", headers=h)
    again = client.post(f"/api/v1/compras/{pid}/aprovar", headers=h)
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_state"
