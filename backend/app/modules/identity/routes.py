from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import set_tenant
from app.core.deps import current_actor, get_db, get_tenant_db
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.models import Store, Unit
from app.modules.identity.models import RefreshToken, Tenant, User
from app.modules.identity.schemas import (
    AuthResponse,
    LoginRequest,
    MeOut,
    RegisterRequest,
    UserOut,
)
from app.modules.identity.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(tags=["auth"])

DEFAULT_UNITS = [
    ("kg", "Quilograma", "mass"),
    ("g", "Grama", "mass"),
    ("ml", "Mililitro", "volume"),
    ("l", "Litro", "volume"),
    ("un", "Unidade", "count"),
]


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=get_settings().cookie_secure,
        samesite="lax",
        max_age=60 * 60 * 24 * get_settings().refresh_token_ttl_days,
        path="/api/v1/auth",
    )


def _issue_tokens(response: Response, db: Session, user: User) -> AuthResponse:
    """Grava refresh_token + commita a transação pendente e emite access+refresh."""
    access = create_access_token(
        actor_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role
    )
    raw = generate_refresh_token()
    db.add(
        RefreshToken(
            tenant_id=user.tenant_id,
            user_id=user.id,
            token_hash=hash_refresh_token(raw),
            expires_at=datetime.now(UTC)
            + timedelta(days=get_settings().refresh_token_ttl_days),
        )
    )
    db.commit()
    _set_cookie(response, raw)
    return AuthResponse(access_token=access, user=UserOut.model_validate(user))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest, response: Response, db: Session = Depends(get_db)  # noqa: B008
) -> AuthResponse:
    if db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug)):
        raise DomainError(
            "tenant_slug_taken", "Já existe um tenant com esse slug.", status.HTTP_409_CONFLICT
        )
    if db.scalar(select(User).where(User.email == payload.email)):
        raise DomainError(
            "email_taken", "Já existe um usuário com esse email.", status.HTTP_409_CONFLICT
        )

    tenant = Tenant(name=payload.tenant_name, slug=payload.tenant_slug, status="active")
    db.add(tenant)
    db.flush()
    set_tenant(db, tenant.id)

    db.add(Store(tenant_id=tenant.id, name="Loja principal", status="active"))
    for symbol, name, typ in DEFAULT_UNITS:
        db.add(Unit(tenant_id=tenant.id, name=name, symbol=symbol, type=typ))

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="owner",
        status="active",
    )
    db.add(user)
    db.flush()

    return _issue_tokens(response, db, user)


@router.post("/login")
def login(
    payload: LoginRequest, response: Response, db: Session = Depends(get_db)  # noqa: B008
) -> AuthResponse:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    user = (
        db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == payload.email))
        if tenant
        else None
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise DomainError(
            "invalid_credentials", "Credenciais inválidas.", status.HTTP_401_UNAUTHORIZED
        )
    if user.status != "active" or (tenant is not None and tenant.status != "active"):
        raise DomainError(
            "invalid_credentials", "Credenciais inválidas.", status.HTTP_401_UNAUTHORIZED
        )
    user.last_login_at = datetime.now(UTC)
    return _issue_tokens(response, db, user)


@router.post("/refresh")
def refresh(
    request: Request, response: Response, db: Session = Depends(get_db)  # noqa: B008
) -> AuthResponse:
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise DomainError("invalid_token", "Sessão ausente.", status.HTTP_401_UNAUTHORIZED)
    tok = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    if tok is None:
        raise DomainError(
            "invalid_token", "Sessão expirada ou inválida.", status.HTTP_401_UNAUTHORIZED
        )

    tok.revoked_at = datetime.now(UTC)
    user = db.get(User, tok.user_id)
    if user is None:
        raise DomainError(
            "invalid_token", "Sessão expirada ou inválida.", status.HTTP_401_UNAUTHORIZED
        )

    return _issue_tokens(response, db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request, response: Response, db: Session = Depends(get_db)  # noqa: B008
) -> None:
    raw = request.cookies.get("refresh_token")
    if raw:
        tok = db.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw))
        )
        if tok is not None:
            tok.revoked_at = datetime.now(UTC)
            db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me")
def me(
    actor: Actor = Depends(current_actor), db: Session = Depends(get_tenant_db)  # noqa: B008
) -> MeOut:
    user = db.get(User, actor.id)
    if user is None or user.tenant_id != actor.tenant_id:
        raise DomainError("unauthorized", "Sessão inválida.", status.HTTP_401_UNAUTHORIZED)
    tenant = db.get(Tenant, actor.tenant_id)
    if tenant is None:
        raise DomainError("unauthorized", "Sessão inválida.", status.HTTP_401_UNAUTHORIZED)
    return MeOut(id=user.id, name=user.name, email=user.email, role=user.role,
                 tenant_id=tenant.id, tenant_name=tenant.name, tenant_slug=tenant.slug)
