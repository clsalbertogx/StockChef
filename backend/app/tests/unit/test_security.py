from app.modules.identity.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_roundtrip() -> None:
    h = hash_password("senha-segura")
    assert h != "senha-segura"
    assert verify_password("senha-segura", h)
    assert not verify_password("errada", h)


def test_access_token_roundtrip() -> None:
    token = create_access_token(actor_id="u1", tenant_id="t1", role="owner")
    payload = decode_access_token(token)
    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["role"] == "owner"
