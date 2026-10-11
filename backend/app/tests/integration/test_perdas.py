from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth(slug: str, email: str = "dono@x.com") -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": email,
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _insumo(h, name: str, avg: str, stock: str) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg",
        "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_perda_baixa_estoque() -> None:
    h = _auth("perdas")
    iid = _insumo(h, "Queijo", "45.00", "3.000")
    resp = client.post("/api/v1/perdas", headers=h, json={
        "ingredient_id": iid, "quantity": "1.000", "reason": "damage",
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["quantity"] == "1.0000"

    ins = client.get(f"/api/v1/insumos/{iid}", headers=h).json()
    assert ins["stock_total"] == "2.00"  # 3 − 1


def test_perda_motivo_invalido_422() -> None:
    h = _auth("perdas2")
    iid = _insumo(h, "Pão", "2.00", "10")
    resp = client.post("/api/v1/perdas", headers=h, json={
        "ingredient_id": iid, "quantity": "1", "reason": "foi-com-embora",
    })
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"


def test_perda_saldo_insuficiente_409() -> None:
    h = _auth("perdas3")
    iid = _insumo(h, "Carne", "30.00", "0.500")
    resp = client.post("/api/v1/perdas", headers=h, json={
        "ingredient_id": iid, "quantity": "2", "reason": "expiration",
    })
    assert resp.status_code == 409
    assert resp.json()["code"] == "invalid_stock_operation"


def test_perda_insumo_sem_stock_level_erro_dominio() -> None:
    h = _auth("perdas4")
    iid = _insumo(h, "Sal", "1.00", "0")  # nunca estocado: sem linha em stock_levels
    resp = client.post("/api/v1/perdas", headers=h, json={
        "ingredient_id": iid, "quantity": "1", "reason": "damage",
    })
    # cria o stock level e falha por saldo insuficiente (domínio), não 404 no_stock_level
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "invalid_stock_operation"
