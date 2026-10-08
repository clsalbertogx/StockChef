"""Alembic migration 0002 - constraints aditivas p/ corridas + default JSONB.

1. unique parcial em customers(tenant_id, phone): a upsert por telefone na
   criacao de pedido usa check-then-insert; sem a constraint, uma corrida
   duplicaria o cliente. Onde phone e NULL, permite multiplos (clientes sem
   telefone).
2. order_items.recipe_snapshot passa a default '[]' (o ORM grava uma lista);
   o DDL do backlog usava '{}' (dict), divergente do formato real.
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_tenant_phone"
        " ON customers(tenant_id, phone) WHERE phone IS NOT NULL;"
    )
    op.execute(
        "ALTER TABLE order_items"
        " ALTER COLUMN recipe_snapshot SET DEFAULT '[]'::jsonb;"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_customers_tenant_phone;")
    op.execute(
        "ALTER TABLE order_items"
        " ALTER COLUMN recipe_snapshot SET DEFAULT '{}'::jsonb;"
    )