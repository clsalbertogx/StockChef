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
