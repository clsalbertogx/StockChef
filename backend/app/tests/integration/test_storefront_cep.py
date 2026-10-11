from fastapi.testclient import TestClient

from app.main import app
from app.modules.storefront import viacep

client = TestClient(app)


def _seed(slug: str) -> None:
    client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })


def test_cep_retorna_endereco(monkeypatch) -> None:
    _seed("cep1")
    monkeypatch.setattr(viacep, "lookup", lambda cep: {
        "cep": "01001000", "street": "Praça da Sé", "district": "Sé",
        "city": "São Paulo", "state": "SP",
    })
    r = client.get("/api/v1/public/cep1/cep/01001000")
    assert r.status_code == 200, r.text
    assert r.json()["city"] == "São Paulo"


def test_cep_invalido_422() -> None:
    _seed("cep2")
    r = client.get("/api/v1/public/cep2/cep/123")
    assert r.status_code == 422, r.text


def test_cep_nao_encontrado_404(monkeypatch) -> None:
    _seed("cep3")

    def _raise(cep: str) -> dict:
        raise viacep.ViaCepError("not_found")

    monkeypatch.setattr(viacep, "lookup", _raise)
    r = client.get("/api/v1/public/cep3/cep/99999999")
    assert r.status_code == 404 and r.json()["code"] == "cep_not_found"


def test_cep_indisponivel_503(monkeypatch) -> None:
    _seed("cep4")

    def _raise(cep: str) -> dict:
        raise viacep.ViaCepError("unavailable")

    monkeypatch.setattr(viacep, "lookup", _raise)
    r = client.get("/api/v1/public/cep4/cep/01001000")
    assert r.status_code == 503 and r.json()["code"] == "cep_unavailable"
