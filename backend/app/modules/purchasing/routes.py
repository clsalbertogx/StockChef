from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import current_actor, get_tenant_db
from app.core.tenant import Actor
from app.modules.catalog.service import default_store
from app.modules.purchasing.service import purchase_suggestion

router = APIRouter()

@router.get("/compras/sugestao")
def compras_sugestao(
    dias: int = 14,
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(current_actor),  # noqa: B008
) -> list[dict]:
    tid = actor.tenant_id
    store_id = default_store(db, tid).id
    return purchase_suggestion(db, tid, store_id, days=dias)
