from uuid import UUID

import pytest

from app.core.deps import require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor


def _actor(role: str) -> Actor:
    return Actor(
        id=UUID("11111111-1111-1111-1111-111111111111"),
        tenant_id=UUID("22222222-2222-2222-2222-222222222222"),
        role=role,
    )


async def test_require_roles_permite_role() -> None:
    checker = require_roles("owner", "manager")
    assert checker(_actor("manager")).role == "manager"


async def test_require_roles_bloqueia_outra_role() -> None:
    checker = require_roles("owner")
    with pytest.raises(DomainError) as exc:
        checker(_actor("cashier"))
    assert exc.value.http_status == 403
    assert exc.value.code == "forbidden"
