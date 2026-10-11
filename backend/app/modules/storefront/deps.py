from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import set_tenant
from app.core.deps import get_db
from app.core.errors import DomainError
from app.modules.identity.models import Tenant


def get_public_db(slug: str, db: Session = Depends(get_db)) -> Iterator[Session]:  # noqa: B008
    """Resolve o tenant pelo slug (fora do RLS) e ativa o escopo da sessão."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None or tenant.status != "active":
        raise DomainError(
            "store_not_found", "Loja não encontrada.", status.HTTP_404_NOT_FOUND
        )
    set_tenant(db, tenant.id)
    yield db
