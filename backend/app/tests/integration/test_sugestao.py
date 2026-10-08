from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth(slug: str) -> dict[str, str]:
    r = client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": slug,
            "tenant_slug": slug,
            "email": f"{slug}@x.com",
            "password": "senha-segura",
            "name": "Dono",
        },
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_sugestao_ignora_sem_consumo() -> None:
    h = _auth("sug0")
    r = client.post(
        "/api/v1/insumos",
        headers=h,
        json={
            "name": "Parado",
            "base_unit_symbol": "kg",
            "average_cost": "5",
            "initial_stock": "10",
            "minimum_stock": "1",
        },
    )
    iid = r.json()["id"]
    resp = client.get("/api/v1/compras/sugestao", headers=h)
    assert resp.status_code == 200
    sugs = resp.json()
    assert all(s["ingredient_id"] != iid for s in sugs)


def test_sugestao_usa_consumo_14d() -> None:
    h = _auth("sug1")
    # precisa de produto+ficha para gerar venda; usa fluxo completo
    queijo = client.post(
        "/api/v1/insumos",
        headers=h,
        json={
            "name": "Queijo",
            "base_unit_symbol": "kg",
            "average_cost": "45",
            "initial_stock": "3",
            "minimum_stock": "5",
        },
    ).json()["id"]
    p = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X", "price": "20"}
    ).json()["id"]
    client.post(
        f"/api/v1/produtos/{p}/ficha-tecnica",
        headers=h,
        json={
            "items": [{"ingredient_id": queijo, "quantity": "0.5"}],
        },
    )
    order = client.post(
        "/api/v1/pedidos",
        headers=h,
        json={"items": [{"product_id": p, "quantity": 2}]},
    ).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)

    resp = client.get("/api/v1/compras/sugestao", headers=h)
    assert resp.status_code == 200
    sugs = resp.json()
    suj = next(s for s in sugs if s["ingredient_id"] == queijo)
    assert Decimal(suj["consumption_daily"]) > 0
    assert Decimal(suj["suggested_quantity"]) > 0
    assert suj["reason"]
