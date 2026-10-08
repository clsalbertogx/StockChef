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


def _insumo(h, name: str, avg: str, stock: str) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_inventario_ajuste_por_diferenca() -> None:
    h = _auth("invent")
    iid = _insumo(h, "Farinha", "5.00", "10.000")
    count = client.post("/api/v1/inventarios", headers=h).json()
    cid = count["id"]
    assert count["status"] == "open"

    # conta 8 em vez de 10
    resp = client.post(f"/api/v1/inventarios/{cid}/itens", headers=h, json={
        "items": [{"ingredient_id": iid, "counted_quantity": "8"}],
    })
    assert resp.status_code == 200

    close = client.post(f"/api/v1/inventarios/{cid}/fechar", headers=h)
    assert close.status_code == 200
    assert close.json()["status"] == "closed"
    item = next(i for i in close.json()["items"] if i["ingredient_id"] == iid)
    assert item["difference"] == "-2.0000"
    assert item["adjusted"] is True

    ins = client.get(f"/api/v1/insumos/{iid}", headers=h).json()
    assert ins["stock_total"] == "8.00"  # ajustado pela diferença (−2)

    # não pode reabrir/contar de novo
    again = client.post(f"/api/v1/inventarios/{cid}/itens", headers=h, json={
        "items": [{"ingredient_id": iid, "counted_quantity": "9"}],
    })
    assert again.status_code == 409
    assert again.json()["code"] == "invalid_state"

    # listagem e detalhe
    listed = client.get("/api/v1/inventarios", headers=h)
    assert listed.status_code == 200
    assert [c["id"] for c in listed.json()] == [cid]
    got = client.get(f"/api/v1/inventarios/{cid}", headers=h)
    assert got.status_code == 200
    assert got.json()["items"][0]["ingredient_id"] == iid

    # outro tenant não enxerga
    h2 = _auth("invent2")
    assert client.get(f"/api/v1/inventarios/{cid}", headers=h2).status_code == 404
