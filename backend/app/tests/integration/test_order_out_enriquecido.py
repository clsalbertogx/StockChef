from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_order_out_expoe_campos_do_ddl() -> None:
    h = _setup("enriq")
    ing = client.post("/api/v1/insumos", headers=h, json={
        "name": "Pao", "base_unit_symbol": "kg", "average_cost": "5.00", "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X-Tudo", "price": "18.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}],
    })
    order = client.post(
        "/api/v1/pedidos", headers=h,
        json={"items": [{"product_id": prod, "quantity": 1}],
              "fulfillment_type": "table", "channel": "pos", "notes": "sem cebola"},
    ).json()
    got = client.get(f"/api/v1/pedidos/{order['id']}", headers=h).json()

    assert got["fulfillment_type"] == "table"
    assert got["channel"] == "pos"
    assert got["delivery_fee"] == "0.00"
    assert got["discount_total"] == "0.00"
    assert got["tax_total"] == "0.00"
    assert got["expected_time"] is None
    # item traz notes/modifiers (jsonb), mesmo que default
    assert got["order_items"][0]["notes"] is None
    assert got["order_items"][0]["modifiers"] == []
