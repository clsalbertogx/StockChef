from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.identity.models import Tenant
from app.modules.storefront.deps import get_public_db
from app.modules.storefront.schemas import PublicMenuOut
from app.modules.storefront.service import current_store, public_menu

router = APIRouter(tags=["storefront"])


@router.get("/public/{slug}/cardapio")
def get_cardapio(
    slug: str,
    q: str | None = Query(default=None, max_length=80),
    category_id: UUID | None = None,
    db: Session = Depends(get_public_db),  # noqa: B008
) -> PublicMenuOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None  # resolvido em get_public_db
    store = current_store(db, tid)
    return public_menu(db, tenant, store, q, category_id)
