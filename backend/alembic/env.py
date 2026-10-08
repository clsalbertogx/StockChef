from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import app.models  # noqa: F401  # registra ORM models no metadata
from app.core.config import get_settings
from app.core.db import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Tabelas do schema do backlog fora do escopo desta fatia (sem ORM).
# `alembic revision --autogenerate` não deve propor DROP para elas.
OUT_OF_SCOPE_TABLES = {
    "plans", "subscriptions", "unit_conversions", "product_modifiers", "zones",
    "drivers", "payments", "deliveries", "proof_of_deliveries", "purchase_orders",
    "purchase_order_items", "goods_receipts", "goods_receipt_items", "losses",
    "inventory_counts", "inventory_count_items", "forecasts", "agent_runs",
    "recommendations", "audit_logs", "usage_metrics",
}


def include_object(object_, name, type_, reflected, compare_to) -> bool:
    if type_ == "table" and reflected and name in OUT_OF_SCOPE_TABLES:
        return False
    return True

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set database URL from environment
url = os.environ.get("ALEMBIC_DATABASE_URL") or get_settings().alembic_database_url
config.set_main_option("sqlalchemy.url", url)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=False,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=False,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
