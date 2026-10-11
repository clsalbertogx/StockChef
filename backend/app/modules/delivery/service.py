from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.delivery.models import Zone


def normalize_cep(cep: str) -> str:
    return "".join(ch for ch in cep if ch.isdigit())


def resolve_zone(db: Session, store_id: UUID, cep: str) -> Zone | None:
    normalized = normalize_cep(cep)
    if len(normalized) != 8:
        return None
    zones = db.scalars(
        select(Zone).where(Zone.store_id == store_id, Zone.active.is_(True))
    ).all()
    for zone in zones:
        for rng in zone.cep_ranges or []:
            start = normalize_cep(str(rng.get("start", "")))
            end = normalize_cep(str(rng.get("end", "")))
            if len(start) == 8 and len(end) == 8 and start <= normalized <= end:
                return zone
    return None
