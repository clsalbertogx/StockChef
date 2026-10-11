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


def _product(h: dict[str, str], name: str) -> str:
    r = client.post("/api/v1/produtos", headers=h, json={"name": name, "price": "20.00"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_cria_e_lista_adicionais() -> None:
    h = _setup("adic1")
    pid = _product(h, "X-Burger")
    r = client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Ponto", "modifier_name": "Ao ponto", "price_delta": "0.00",
        "required": True, "min_selection": 1, "max_selection": 1,
    })
    assert r.status_code == 201, r.text
    assert r.json()["modifier_name"] == "Ao ponto"
    r2 = client.get(f"/api/v1/produtos/{pid}/adicionais", headers=h)
    assert r2.status_code == 200 and len(r2.json()) == 1


def test_patch_desativa_adicional() -> None:
    h = _setup("adic2")
    pid = _product(h, "X-Burger")
    mid = client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Extras", "modifier_name": "Bacon", "price_delta": "3.00",
    }).json()["id"]
    r = client.patch(f"/api/v1/produtos/{pid}/adicionais/{mid}", headers=h,
                     json={"active": False})
    assert r.status_code == 200 and r.json()["active"] is False


def test_produto_inexistente_404() -> None:
    h = _setup("adic3")
    r = client.post("/api/v1/produtos/00000000-0000-0000-0000-000000000000/adicionais",
                    headers=h, json={"group_name": "X", "modifier_name": "Y"})
    assert r.status_code == 404, r.text
