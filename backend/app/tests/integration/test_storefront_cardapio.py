from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _seed(slug: str) -> None:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "25.00"})
    pid = p.json()["id"]
    client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Ponto", "modifier_name": "Ao ponto", "required": True,
        "min_selection": 1, "max_selection": 1,
    })


def test_cardapio_publico_sem_auth() -> None:
    _seed("menu1")
    r = client.get("/api/v1/public/menu1/cardapio")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant"]["slug"] == "menu1"
    assert len(body["products"]) == 1
    assert body["products"][0]["name"] == "X-Burger"
    assert body["products"][0]["modifiers"][0]["modifier_name"] == "Ao ponto"


def test_busca_e_filtro() -> None:
    _seed("menu2")
    r = client.get("/api/v1/public/menu2/cardapio", params={"q": "burger"})
    assert len(r.json()["products"]) == 1
    r2 = client.get("/api/v1/public/menu2/cardapio", params={"q": "inexistente"})
    assert r2.json()["products"] == []


def test_slug_inexistente_404() -> None:
    r = client.get("/api/v1/public/nao-existe/cardapio")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "store_not_found"


def test_isolamento_entre_tenants() -> None:
    _seed("menu3")
    _seed("menu4")
    assert client.get("/api/v1/public/menu3/cardapio").json()["tenant"]["slug"] == "menu3"
