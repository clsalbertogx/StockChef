from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import pytest
import sqlalchemy as sa
from testcontainers.postgres import PostgresContainer

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[3]


def pytest_configure(config: pytest.Config) -> None:
    pg = PostgresContainer("postgres:16-alpine")
    pg.start()
    config._pg = pg  # type: ignore[attr-defined]
    host = pg.get_container_host_ip()
    port = pg.get_exposed_port(5432)
    admin_url = f"postgresql+psycopg://test:test@{host}:{port}/test"
    app_url = f"postgresql+psycopg://stockchef_app:stockchef_app@{host}:{port}/test"
    os.environ["ALEMBIC_DATABASE_URL"] = admin_url
    os.environ["DATABASE_URL"] = app_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
        env={**os.environ, "ALEMBIC_DATABASE_URL": admin_url},
    )


def pytest_unconfigure(config: pytest.Config) -> None:
    pg = getattr(config, "_pg", None)
    if pg is not None:
        pg.stop()


@pytest.fixture(autouse=True)
def clean_db() -> None:
    """Trunca o banco antes de cada teste."""
    before = os.environ.get("ALEMBIC_DATABASE_URL")
    engine = sa.create_engine(
        before or "postgresql+psycopg://test:test@localhost:5432/test",
        connect_args={"connect_timeout": 1},
    )
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("TRUNCATE tenants, plans RESTART IDENTITY CASCADE"))
    except (sa.exc.OperationalError, sa.exc.ProgrammingError):
        pass
    finally:
        engine.dispose()
