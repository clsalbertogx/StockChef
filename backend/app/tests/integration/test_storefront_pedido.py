from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _seed(slug: str, *, with_zone: bool = True) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if with_zone:
        client.post("/api/v1/zonas", headers=h, json={
            "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
            "delivery_fee": "6.00", "min_order_value": "10.00", "eta_minutes": 35,
        })
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "25.00"})
    return h, p.json()["id"]


def _body(pid: str, **over) -> dict:
    body = {
        "customer_name": "Ana", "customer_phone": "11999999999",
        "fulfillment_type": "delivery", "cep": "01001000",
        "address": {"street": "Sé", "number": "1", "district": "Sé", "city": "SP", "state": "SP"},
        "idempotency_key": "chave-publica-0001",
        "items": [{"product_id": pid, "quantity": 1, "modifier_ids": []}],
    }
    body.update(over)
    return body


def test_cria_pedido_publico_com_taxa() -> None:
    _h, pid = _seed("pub1")
    r = client.post("/api/v1/public/pub1/pedidos", json=_body(pid))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subtotal"] == "25.00" and body["delivery_fee"] == "6.00"
    assert body["total"] == "31.00" and body["status"] == "received"
    assert body["eta_minutes"] == 35
    code = body["code"]

    got = client.get(f"/api/v1/public/pub1/pedidos/{code}")
    assert got.status_code == 200 and got.json()["code"] == code


def test_idempotencia_nao_duplica() -> None:
    _h, pid = _seed("pub2")
    r1 = client.post("/api/v1/public/pub2/pedidos", json=_body(pid))
    r2 = client.post("/api/v1/public/pub2/pedidos", json=_body(pid))
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["code"] == r2.json()["code"]


def test_pickup_sem_taxa() -> None:
    _h, pid = _seed("pub3", with_zone=False)
    r = client.post("/api/v1/public/pub3/pedidos", json=_body(
        pid, fulfillment_type="pickup", cep=None, address=None,
        idempotency_key="chave-pickup-0001",
    ))
    assert r.status_code == 201, r.text
    assert r.json()["delivery_fee"] == "0.00" and r.json()["total"] == "25.00"


def test_cep_nao_coberto_422() -> None:
    _h, pid = _seed("pub4")
    r = client.post("/api/v1/public/pub4/pedidos", json=_body(
        pid, cep="99999999", idempotency_key="chave-fora-0001",
    ))
    assert r.status_code == 422 and r.json()["code"] == "cep_not_covered"


def test_abaixo_do_minimo_422() -> None:
    h, _pid = _seed("pub5")
    p = client.post("/api/v1/produtos", headers=h, json={"name": "Água", "price": "3.00"}).json()
    r = client.post("/api/v1/public/pub5/pedidos", json=_body(
        p["id"], idempotency_key="chave-min-0001",
    ))
    assert r.status_code == 422 and r.json()["code"] == "below_min_order"


def test_adicional_invalido_422() -> None:
    _h, pid = _seed("pub6")
    r = client.post("/api/v1/public/pub6/pedidos", json=_body(pid, items=[
        {
            "product_id": pid,
            "quantity": 1,
            "modifier_ids": ["00000000-0000-0000-0000-000000000000"],
        },
    ], idempotency_key="chave-mod-0001"))
    assert r.status_code == 422 and r.json()["code"] == "invalid_modifiers"


def test_delivery_desabilitada_422_fulfillment_unavailable() -> None:
    """Loja com delivery_enabled=False deve recusar pedido delivery."""
    from sqlalchemy import select

    from app.core.db import SessionLocal, set_tenant
    from app.modules.catalog.models import Store
    from app.modules.identity.models import Tenant

    h, pid = _seed("pub7")
    db = SessionLocal()
    try:
        t = db.scalar(select(Tenant).where(Tenant.slug == "pub7"))
        assert t is not None
        set_tenant(db, t.id)
        store = db.scalar(select(Store).where(Store.tenant_id == t.id, Store.status == "active"))
        if store:
            store.delivery_enabled = False
            db.commit()
    finally:
        db.close()

    r = client.post("/api/v1/public/pub7/pedidos", json=_body(
        pid, idempotency_key="chave-del-dis-0001",
    ))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "fulfillment_unavailable"


def test_pickup_desabilitada_422_fulfillment_unavailable() -> None:
    """Loja com pickup_enabled=False deve recusar pedido pickup."""
    from sqlalchemy import select

    from app.core.db import SessionLocal, set_tenant
    from app.modules.catalog.models import Store
    from app.modules.identity.models import Tenant

    h, pid = _seed("pub8")
    db = SessionLocal()
    try:
        t = db.scalar(select(Tenant).where(Tenant.slug == "pub8"))
        assert t is not None
        set_tenant(db, t.id)
        store = db.scalar(select(Store).where(Store.tenant_id == t.id, Store.status == "active"))
        if store:
            store.pickup_enabled = False
            db.commit()
    finally:
        db.close()

    r = client.post("/api/v1/public/pub8/pedidos", json=_body(
        pid, fulfillment_type="pickup", cep=None, address=None,
        idempotency_key="chave-pick-dis-0001",
    ))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "fulfillment_unavailable"


def test_scheduled_time_respeitado() -> None:
    """Pedido com scheduled_time deve ter expected_time = scheduled_time."""
    from datetime import UTC, datetime, timedelta

    _h, pid = _seed("pub9")
    scheduled = (datetime.now(UTC) + timedelta(minutes=120)).isoformat()
    r = client.post("/api/v1/public/pub9/pedidos", json=_body(
        pid, scheduled_time=scheduled, idempotency_key="chave-sched-0001",
    ))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["eta_minutes"] is not None and body["eta_minutes"] >= 115


def test_modificadores_duplicados_422() -> None:
    """Duplicar modifier_ids no mesmo item deve falhar com invalid_modifiers."""
    _h, pid = _seed("pub10")
    r = client.post("/api/v1/public/pub10/pedidos", json={
        "customer_name": "Ana", "customer_phone": "11999999999",
        "fulfillment_type": "delivery", "cep": "01001000",
        "address": {"street": "Sé", "number": "1", "district": "Sé", "city": "SP", "state": "SP"},
        "idempotency_key": "chave-dup-0001",
        "items": [{
            "product_id": pid,
            "quantity": 1,
            "modifier_ids": ["00000000-0000-0000-0000-000000000001",
                           "00000000-0000-0000-0000-000000000001"],
        }],
    })
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "invalid_modifiers"


def test_produto_cross_tenant_404() -> None:
    """Produto de outro tenant não deve ser acessível no cardápio/pedido."""
    h1, pid1 = _seed("pub11a")
    _h2, pid2 = _seed("pub11b")

    r = client.post("/api/v1/public/pub11a/pedidos", json={
        "customer_name": "Ana", "customer_phone": "11999999999",
        "fulfillment_type": "delivery", "cep": "01001000",
        "address": {"street": "Sé", "number": "1", "district": "Sé", "city": "SP", "state": "SP"},
        "idempotency_key": "chave-cross-0001",
        "items": [{"product_id": pid2, "quantity": 1, "modifier_ids": []}],
    })
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "product_not_found"
