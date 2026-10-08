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


def test_criar_e_listar_fornecedores() -> None:
    h = _auth("forn")
    resp = client.post("/api/v1/fornecedores", headers=h, json={
        "name": "Laticínios ABC", "lead_time_days": 2,
    })
    assert resp.status_code == 201, resp.text
    fid = resp.json()["id"]

    lista = client.get("/api/v1/fornecedores", headers=h).json()
    assert [f["id"] for f in lista] == [fid]

    one = client.get(f"/api/v1/fornecedores/{fid}", headers=h)
    assert one.status_code == 200
    assert one.json()["name"] == "Laticínios ABC"
    assert one.json()["lead_time_days"] == 2


def test_update_delete_fornecedor() -> None:
    h = _auth("forn-upd")
    resp = client.post("/api/v1/fornecedores", headers=h, json={
        "name": "Fornecedor Original", "lead_time_days": 1,
    })
    assert resp.status_code == 201
    fid = resp.json()["id"]

    # Patch
    patch = client.patch(f"/api/v1/fornecedores/{fid}", headers=h, json={
        "name": "Fornecedor Novo", "lead_time_days": 5,
    })
    assert patch.status_code == 200
    assert patch.json()["name"] == "Fornecedor Novo"
    assert patch.json()["lead_time_days"] == 5

    # Delete
    d = client.delete(f"/api/v1/fornecedores/{fid}", headers=h)
    assert d.status_code == 204

    # Verify deleted
    get = client.get(f"/api/v1/fornecedores/{fid}", headers=h)
    assert get.status_code == 404
