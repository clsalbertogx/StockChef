from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _owner(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_cria_lista_e_patch_zona() -> None:
    h = _owner("zona1")
    r = client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
        "delivery_fee": "7.50", "min_order_value": "20.00", "eta_minutes": 40,
    })
    assert r.status_code == 201, r.text
    zid = r.json()["id"]
    assert r.json()["delivery_fee"] == "7.50"
    lst = client.get("/api/v1/zonas", headers=h)
    assert lst.status_code == 200 and len(lst.json()) == 1
    p = client.patch(f"/api/v1/zonas/{zid}", headers=h, json={"active": False})
    assert p.status_code == 200 and p.json()["active"] is False


def test_cep_normalizado_com_mascara() -> None:
    h = _owner("zona2")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Zona A", "cep_ranges": [{"start": "20000000", "end": "20999999"}],
        "delivery_fee": "5.00",
    })
    from sqlalchemy import select

    from app.core.db import SessionLocal, set_tenant
    from app.modules.delivery.service import resolve_zone
    from app.modules.identity.models import Tenant

    db = SessionLocal()
    try:
        t = db.scalar(select(Tenant).where(Tenant.slug == "zona2"))
        assert t is not None
        set_tenant(db, t.id)
        from app.modules.catalog.service import default_store

        store = default_store(db, t.id)
        assert resolve_zone(db, store.id, "20000-100") is not None
        assert resolve_zone(db, store.id, "99999999") is None
    finally:
        db.close()
