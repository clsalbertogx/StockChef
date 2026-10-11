from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _owner(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_entrega_com_zona_coberta() -> None:
    h = _owner("ent1")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
        "delivery_fee": "8.00", "min_order_value": "15.00", "eta_minutes": 45,
    })
    r = client.get("/api/v1/public/ent1/entrega", params={"cep": "01001000"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["covered"] is True and body["delivery_fee"] == "8.00"
    assert body["eta_minutes"] == 45


def test_entrega_cep_fora_retorna_nao_coberto() -> None:
    h = _owner("ent2")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
    })
    r = client.get("/api/v1/public/ent2/entrega", params={"cep": "99999999"})
    assert r.json()["covered"] is False


def test_entrega_sem_zonas_fallback() -> None:
    _owner("ent3")
    r = client.get("/api/v1/public/ent3/entrega", params={"cep": "01001000"})
    body = r.json()
    assert body["covered"] is True and body["delivery_fee"] == "0.00"
    assert body["eta_minutes"] == 30
