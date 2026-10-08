from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, set_tenant
from app.core.errors import DomainError
from app.core.tenant import Actor


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def current_actor(request: Request) -> Actor:
    actor: Actor | None = getattr(request.state, "actor", None)
    if actor is None:
        raise DomainError("unauthorized", "Autenticação necessária.", status.HTTP_401_UNAUTHORIZED)
    return actor


def get_tenant_db(
    actor: Actor = Depends(current_actor), db: Session = Depends(get_db)  # noqa: B008
) -> Iterator[Session]:
    set_tenant(db, actor.tenant_id)
    yield db
