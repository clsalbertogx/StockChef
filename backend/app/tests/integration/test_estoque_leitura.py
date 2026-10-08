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


def _insumo(h, name: str, avg: str, stock: str, minimum: str = "0") -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg,
        "initial_stock": stock, "minimum_stock": minimum,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_critico_lista_abaixo_do_minimo() -> None:
    h = _auth("critico")
    _insumo(h, "Acima", "45.00", "3.000", "1")
    iid = _insumo(h, "Abaixo", "45.00", "0.500", "1")
    resp = client.get("/api/v1/estoque/critico", headers=h)
    assert resp.status_code == 200
    crit = resp.json()
    assert [c["name"] for c in crit] == ["Abaixo"]
    assert crit[0]["ingredient_id"] == iid


def test_movimentos_lista_vendas_e_perdas() -> None:
    h = _auth("movs")
    iid = _insumo(h, "Queijo", "45.00", "3.000")
    client.post("/api/v1/perdas", headers=h, json={
        "ingredient_id": iid, "quantity": "0.500", "reason": "damage",
    })
    resp = client.get(f"/api/v1/estoque/movimentos?ingredient_id={iid}", headers=h)
    assert resp.status_code == 200
    movs = resp.json()
    assert len(movs) == 1
    assert movs[0]["type"] == "loss"
    assert movs[0]["quantity"] == "-0.5000"
