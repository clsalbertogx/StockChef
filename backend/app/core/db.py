from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def create_engine(url: str) -> sa.Engine:
    return sa.create_engine(url, pool_pre_ping=True)


engine = create_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _set_tenant_config(session: Session, tenant_id: str | None) -> None:
    session.execute(
        sa.text("SELECT set_config('app.tenant_id', :tid, true)"),
        {"tid": tenant_id},
    )


@event.listens_for(Session, "after_begin")
def _apply_tenant(session: Session, transaction: object) -> None:
    _set_tenant_config(session, session.info.get("tenant_id"))


def set_tenant(session: Session, tenant_id: UUID | str | None) -> None:
    value = None if tenant_id is None else str(tenant_id)
    session.info["tenant_id"] = value
    if session.in_transaction():
        _set_tenant_config(session, value)
