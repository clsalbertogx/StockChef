import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.core.db import SessionLocal, set_tenant
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client_: TestClient, slug: str, email: str) -> None:
    resp = client_.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug,
        "email": email, "password": "senha-segura", "name": "Dono",
    })
    assert resp.status_code == 201, resp.text


def _tenant_id(slug: str) -> str:
    session = SessionLocal()
    try:
        row = session.execute(sa_text("SELECT id FROM tenants WHERE slug = :s"), {"s": slug}).one()
        return str(row[0])
    finally:
        session.close()


def test_register_creates_tenant_units_and_store(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Lanches Sul", "tenant_slug": "lanches-sul",
        "email": "dono@sul.example", "password": "senha-segura", "name": "Dona",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "dono@sul.example"
    assert body["user"]["role"] == "owner"


def test_register_duplicate_slug(client: TestClient) -> None:
    _register(client, "unico", "a@b.com")
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Outro", "tenant_slug": "unico",
        "email": "c@d.com", "password": "senha-segura", "name": "XX",
    })
    assert resp.status_code == 409
    assert resp.json()["code"] == "tenant_slug_taken"


def test_login_uniform_failure(client: TestClient) -> None:
    _register(client, "segredo", "segredo@x.com")
    for payload in (
        {"tenant_slug": "segredo", "email": "segredo@x.com", "password": "errada"},
        {"tenant_slug": "nao-existe", "email": "segredo@x.com", "password": "senha-segura"},
    ):
        resp = client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401, resp.text
        assert resp.json()["code"] == "invalid_credentials"


def test_refresh_rotates_and_logout_revokes(client: TestClient) -> None:
    _register(client, "rotacao", "rotacao@x.com")
    resp = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "rotacao", "email": "rotacao@x.com", "password": "senha-segura"},
    )
    assert resp.status_code == 200
    c1 = resp.cookies["refresh_token"]
    access = resp.json()["access_token"]

    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.cookies["refresh_token"] != c1

    r2 = client.post("/api/v1/auth/refresh", cookies={"refresh_token": c1})
    assert r2.status_code == 401  # cookie antigo rotacionado foi revogado

    client.headers.update({"Authorization": f"Bearer {access}"})
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_rls_isolation_stores(client: TestClient) -> None:
    _register(client, "pizzaria-norte", "norte@x.com")
    _register(client, "hamburgueria-sul", "sul@x.com")

    session = SessionLocal()
    try:
        set_tenant(session, _tenant_id("pizzaria-norte"))
        rows = session.execute(sa_text("SELECT name FROM stores")).all()
        assert [r[0] for r in rows] == ["Loja principal"]
    finally:
        session.close()

    session = SessionLocal()
    try:
        set_tenant(session, None)
        assert session.execute(sa_text("SELECT 1 FROM stores")).fetchall() == []
    finally:
        session.close()


def test_header_tenant_mismatch_403(client: TestClient) -> None:
    _register(client, "norte", "norte2@x.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"tenant_slug": "norte", "email": "norte2@x.com", "password": "senha-segura"},
    )
    token = login.json()["access_token"]
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": str(uuid.uuid4())},
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "tenant_mismatch"


def test_register_duplicate_email_409(client: TestClient) -> None:
    _register(client, "em-1", "dup@x.com")
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Outro", "tenant_slug": "em-2",
        "email": "dup@x.com", "password": "senha-segura", "name": "XX",
    })
    assert resp.status_code == 409
    assert resp.json()["code"] == "email_taken"


def test_login_inactive_user_rejected(client: TestClient) -> None:
    _register(client, "inativo", "inativo@x.com")
    session = SessionLocal()
    try:
        session.execute(
            sa_text("UPDATE users SET status = 'disabled' WHERE email = :e"),
            {"e": "inativo@x.com"},
        )
        session.commit()
    finally:
        session.close()
    resp = client.post("/api/v1/auth/login", json={
        "tenant_slug": "inativo", "email": "inativo@x.com", "password": "senha-segura",
    })
    assert resp.status_code == 401
    assert resp.json()["code"] == "invalid_credentials"


def test_login_password_over_72_chars_422(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/login", json={
        "tenant_slug": "x", "email": "a@b.com", "password": "p" * 73,
    })
    assert resp.status_code == 422
    assert resp.json()["code"] == "validation_error"
