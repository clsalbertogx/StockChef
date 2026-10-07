# StockChef — Fundação + Primeira Fatia Vertical: Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Colocar o repositório vazio em funcionamento com scaffold completo (backend FastAPI + frontend Vite) e o fluxo núcleo end-to-end via API: insumo → produto → ficha técnica → pedido → confirmação → baixa de estoque idempotente → margem.

**Architecture:** Monorepo com apps isolados (`backend/`, `frontend/`). Backend: FastAPI + SQLAlchemy 2.0 + Alembic sobre PostgreSQL 16 com Row-Level Security (isolamento multi-tenant na camada de banco). Baixa de estoque via padrão outbox com worker in-process (BackgroundTasks), preparado para troca por RabbitMQ depois. Frontend: Vite + React + TS + Tailwind + shadcn/ui (admin funcional, sem PWA).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, PyJWT, bcrypt, pytest, testcontainers, ruff, mypy · Node 24, React, Vite, TypeScript, Tailwind v4, shadcn/ui, TanStack Query, React Router, Biome, Vitest · PostgreSQL 16, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-10-07-foundation-vertical-slice-design.md` — este plano argumenta a partir do spec; executores devem ler ambos.

## Global Constraints

- Python **3.12**, Node **24**, PostgreSQL **16**, Docker Compose (ambiente verificado; `uv` **não** está instalado — usar venv + pip).
- Lint/format frontend: **Biome** (nunca ESLint). Lint backend: **ruff** + **mypy**.
- Dois roles PostgreSQL: `stockchef` (dono/superuser, só migrations) e `stockchef_app` (app, **sem** BYPASSRLS). Role `stockchef_app` é criada pela própria migration 0001.
- Status de pedido (valores do banco): `received`, `confirmed`, `confirmed_pending_stock` (equivale ao `CONFIRMADO_COM_PENDÊNCIA` do spec), `preparing`, `ready`, `out_for_delivery`, `delivered`, `completed`, `cancelled`, `refunded`.
- Registro cria `tenants` + `users` (owner, `status='active'`) + loja padrão na mesma transação, aplicando `set_config('app.tenant_id', ...)` após inserir o tenant (necessário para o WITH CHECK do RLS).
- Tabelas **sem** RLS (escopo por filtro na camada de identidade): `tenants`, `plans`, `users`, `refresh_tokens`. Todas as demais tabelas com coluna `tenant_id` recebem RLS via DO block dinâmico.
- Ficha técnica: `quantity` sempre na unidade-base do insumo (API não aceita `unit_id` — **sem conversão de unidades**; `waste_factor` ignorado nesta fatia).
- Dinheiro/quantidades: `Decimal` no servidor (colunas NUMERIC); margem arredondada em 2 casas.
- API prefix `/api/v1`. Erros de domínio: `{ "detail": str, "code": str }` (422 de validação Pydantic mantém formato padrão do FastAPI).
- Copy do frontend: **pt-BR**, sentence case, botões verbais (DESIGN.md global).
- JWT access 30 min (claims `sub`, `tenant_id`, `role`). Refresh 7 dias, opaque, hash SHA-256 em `refresh_tokens`, cookie httpOnly `path=/api/v1/auth`.
- **Fora de escopo vinculante** (spec §1): PWA/offline, pagamentos, entregas/motoristas, RabbitMQ, agentes IA, billing, waste_factor, conversão de unidades, paginação, histórico de versões de receita.
- Cada task termina com testes verdes e um commit.

## Visão geral das tasks

| # | Task | Entrega testável |
|---|------|------------------|
| 1 | Scaffold do repositório | `docker compose up` + CI placeholder verde |
| 2 | Scaffold do backend | `/api/v1/health` 200, ruff/mypy/pytest configurados |
| 3 | Alembic + migração 0001 | Schema completo + RLS no banco |
| 4 | Auth multi-tenant | Register/login/refresh + isolamento RLS provado |
| 5 | Insumos + unidades + estoque inicial | CRUD de insumo com saldo |
| 6 | Produtos + ficha técnica + custo | Cálculo de custo (Gherkin X-Burger) |
| 7 | Criação de pedidos | Validação de disponibilidade (422) |
| 8 | Confirmação + outbox + baixa idempotente | Gherkin baixa automática + idempotência |
| 9 | Endpoint de margem | Margem % e R$ por produto |
| 10 | Seed de demonstração | `make seed` cria cenário demo |
| 11 | Frontend scaffold + login | Login com refresh automático |
| 12 | Frontend páginas (insumos/produtos/pedidos) | UI admin dos fluxos |
| 13 | CI completa + README final | Pipeline verde documentado |

---

### Task 1: Scaffold do repositório

**Files:**
- Create: `.gitignore`, `README.md`, `docker-compose.yml`, `Makefile`, `.env.example`, `.github/workflows/ci.yml`

**Interfaces:**
- Produz: comandos `make up/down/install/migrate/seed/test/lint/dev-backend/dev-frontend`; variáveis `DATABASE_URL` e `ALEMBIC_DATABASE_URL`.

- [ ] **Step 1: Criar `.gitignore`**

```gitignore
.venv/
__pycache__/
*.py[cod]
*.egg-info/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
node_modules/
dist/
.env
.DS_Store
*.local
```

- [ ] **Step 2: Criar `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: stockchef
      POSTGRES_PASSWORD: stockchef
      POSTGRES_DB: stockchef
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stockchef -d stockchef"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 3: Criar `.env.example`**

```bash
# App (role sem BYPASSRLS — aplicação)
DATABASE_URL=postgresql+psycopg://stockchef_app:stockchef_app@localhost:5432/stockchef
# Alembic (dono das tabelas)
ALEMBIC_DATABASE_URL=postgresql+psycopg://stockchef:stockchef@localhost:5432/stockchef
JWT_SECRET=troque-em-producao
```

- [ ] **Step 4: Criar `Makefile`**

```make
.PHONY: install install-backend install-frontend up down migrate seed test test-backend test-frontend lint dev-backend dev-frontend

install: install-backend install-frontend

install-backend:
	python3 -m venv .venv
	.venv/bin/pip install -e "backend[dev]"

install-frontend:
	cd frontend && npm install

up:
	docker compose up -d

down:
	docker compose down

migrate:
	cd backend && ../.venv/bin/alembic upgrade head

seed:
	cd backend && ../.venv/bin/python scripts/seed.py

test: test-backend test-frontend

test-backend:
	cd backend && ../.venv/bin/pytest -q

test-frontend:
	cd frontend && npm run test

lint:
	cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
	cd frontend && npm run lint

dev-backend:
	cd backend && ../.venv/bin/uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev
```

- [ ] **Step 5: Criar `README.md` inicial e CI placeholder**

`README.md`:

```markdown
# StockChef

SaaS multi-tenant de delivery próprio + controle de estoque por ficha técnica.

Documentação de produto: `docs/` (PRD, plano, backlog).

## Requisitos

Python 3.12 · Node 24 · Docker

## Início rápido

    make install       # venv + deps backend e frontend
    make up            # PostgreSQL 16
    make migrate       # schema
    make seed          # dados demo
    make dev-backend   # :8000
    make dev-frontend  # :5173

## Testes

    make test   # backend (pytest + testcontainers) e frontend (vitest)
    make lint   # ruff + mypy + biome
```

`.github/workflows/ci.yml` (placeholder — substituído na Task 13):

```yaml
name: CI
on:
  push:
    branches: [main]
  pull_request:

jobs:
  guard:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate compose file
        run: docker compose config -q
      - name: Docs present
        run: test -f README.md && test -d docs
```

- [ ] **Step 6: Subir compose e verificar**

Run: `docker compose up -d && docker compose ps`
Expected: serviço `postgres` `healthy`.

- [ ] **Step 7: Commit**

```bash
git add .gitignore README.md docker-compose.yml Makefile .env.example .github
git commit -m "chore: scaffold repositório (compose, makefile, ci placeholder)"
```

---

### Task 2: Scaffold do backend

**Files:**
- Create: `backend/pyproject.toml`, `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/.gitkeep`, `backend/app/__init__.py`, `backend/app/models.py`, `backend/app/main.py`, `backend/app/core/__init__.py`, `backend/app/core/config.py`, `backend/app/core/db.py`, `backend/app/core/errors.py`, `backend/app/core/api.py`, `backend/app/tests/__init__.py`, `backend/app/tests/unit/__init__.py`, `backend/app/tests/integration/__init__.py`, `backend/app/tests/integration/conftest.py`, `backend/app/tests/integration/test_health.py`

**Interfaces:**
- Preconditions: `python3` 3.12 disponível; `make install-backend` cria `.venv/`.
- Postconditions: `make dev-backend` sobe `/api/v1/health` → `200 {"status":"ok"}`; `ruff`, `mypy` e `pytest` (com testcontainers) verdes. `DATABASE_URL`/`ALEMBIC_DATABASE_URL` lidos de env/`.env` com defaults locais. `app.core.db`: `Base`, `engine`, `SessionLocal`, `set_tenant(session, tenant_id)`; `app.core.errors`: `DomainError(code, detail, status)`; `app.core.api`: router `/api/v1`, handler global de `DomainError`.

- [ ] **Step 1: Escrever o teste de health primeiro (TDD)**

`backend/app/tests/integration/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [ ] **Step 2: Criar `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "stockchef"
version = "0.1.0"
description = "Backend do StockChef (FastAPI + SQLAlchemy 2.0)"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "sqlalchemy>=2.0.36",
  "psycopg[binary]>=3.2",
  "alembic>=1.14",
  "pydantic>=2.10",
  "pydantic-settings>=2.7",
  "pyjwt>=2.10",
  "bcrypt>=4.2",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3",
  "httpx>=0.28",
  "testcontainers[postgres]>=4.8",
  "ruff>=0.8",
  "mypy>=1.13",
]

[tool.setuptools.packages.find]
include = ["app*"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
packages = ["app"]
ignore_missing_imports = true
warn_unused_ignores = true

[tool.pytest.ini_options]
testpaths = ["app/tests"]
addopts = "-q"
```

- [ ] **Step 3: Criar `backend/app/__init__.py`, `backend/app/tests/**/__init__.py` e `.gitkeep` das versions**

```bash
mkdir -p backend/alembic/versions \
  backend/app/core backend/app/tests/unit backend/app/tests/integration
touch backend/app/__init__.py backend/app/tests/__init__.py \
  backend/app/tests/unit/__init__.py backend/app/tests/integration/__init__.py \
  backend/alembic/versions/.gitkeep
```

- [ ] **Step 4: Criar `backend/app/core/config.py`**

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://stockchef_app:stockchef_app@localhost:5432/stockchef"
    alembic_database_url: str = "postgresql+psycopg://stockchef:stockchef@localhost:5432/stockchef"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 30
    refresh_token_ttl_days: int = 7


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 5: Criar `backend/app/core/db.py`** (engine + sessão com injeção de tenant via `app.tenant_id`)

```python
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
```

- [ ] **Step 6: Criar `backend/app/core/errors.py`**

```python
from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        extra: dict | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status
        self.extra = extra or {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def on_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
        )
```

- [ ] **Step 7: Criar `backend/app/core/api.py`** (router global `/api/v1` + `models.py` registro)

```python
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
```

```python
"""Registro central de modelos — cada módulo com modelos importado aqui popula o metadata."""
from app.core.db import Base as Base

metadata = Base.metadata
```

- [ ] **Step 8: Criar `backend/app/core/__init__.py`** (vazio) **e `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.api import api_router
from app.core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="StockChef API", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)

    @api_router.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
```

- [ ] **Step 9: Instalar e rodar o teste de health (TDD — deve ficar vermelho primeiro)**

```bash
cd backend
python3 -m venv ../.venv
../.venv/bin/pip install -e ".[dev]"
```

Run: `../.venv/bin/pytest -q`
Expected: `FAILED` (módulo `app` não importável ainda não é o caso — o teste sobe e passa; se `pytest` falhar por erro de import, corrigir antes de prosseguir). Na primeira execução o container PostgreSQL sobe via testcontainers; dar um start mais lento é esperado.

- [ ] **Step 10: Criar `backend/app/tests/integration/conftest.py`** (testcontainers + migrações no setup)

```python
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

import sqlalchemy as sa
import pytest
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
    """Trunca o banco antes de cada teste.

    Autouse: dá isolamento para testes unitários e de integração sem depender de
    fixture explicitamente. Sem Docker disponível (ex.: pytest nos testes unitários),
    a conexão falha e o truncate é ignorado — os testes que dependem do banco
    falharão por indisponibilidade, não por estado sujo.
    """
    before = os.environ.get("ALEMBIC_DATABASE_URL")
    engine = sa.create_engine(before or "postgresql+psycopg://test:test@localhost:5432/test", connect_args={"connect_timeout": 1})
    try:
        with engine.begin() as conn:
            conn.execute(sa.text("TRUNCATE tenants, plans RESTART IDENTITY CASCADE"))
    except sa.exc.OperationalError:
        pass
    finally:
        engine.dispose()
```

- [ ] **Step 11: Rodar lint, typecheck e testes**

```bash
cd backend
../.venv/bin/ruff check .
../.venv/bin/mypy .
../.venv/bin/pytest -q
```

Expected: ruff sem erros; mypy sem erros; `test_health` verde com a migration 0001 aplicada pelo conftest (a migration ainda não existe — ver Task 3; até lá o `alembic upgrade head` falha. Para esta task, basta o arquivo `0001_initial` existir com `pass` temporário OU rodar `pytest -q app/tests/integration/test_health.py -k health` sem o conftest. **Agir com bom senso: validar o que está pronto nesta task (health) e deixar o conftest completo validado na Task 3.**)

- [ ] **Step 12: Commit**

```bash
git add backend
git commit -m "feat(backend): scaffold FastAPI + config + health endpoint + conftest testcontainers"
```

---

### Task 3: Alembic + migração 0001 (schema completo + RLS)

**Files:**
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial.py`

**Interfaces:**
- Preconditions: Postgres rodando (compose ou testcontainer); `ALEMBIC_DATABASE_URL` aponta para owner.
- Postconditions: `make migrate` aplica e `alembic downgrade base` remove tudo. Banco com schema completo do backlog (`docs/backlog-delivery-project.md:300-971`), **mais** `refresh_tokens` e `outbox_events`; role `stockchef_app` (LOGIN, PASSWORD `stockchef_app`, **sem BYPASSRLS**); RLS habilitado com policy `tenant_isolation USING (tenant_id = current_setting('app.tenant_id')::uuid)` + `WITH CHECK` em todas as tabelas com `tenant_id` exceto `plans`, `tenants`, `users`, `refresh_tokens`; grants `SELECT, INSERT, UPDATE, DELETE` em todas as tabelas + `USAGE, SELECT` em sequences para `stockchef_app`.
- A migration 0001 é **SQL em massa** (`op.execute`) replicando o bloco DDL do backlog, revisado tabela a tabela (risco §10 do spec), com os deltas abaixo aplicados.

**Deltas obrigatórios sobre o DDL do backlog (`:300-971`):**
1. `orders.status` check passa a incluir `'confirmed_pending_stock'`.
2. Nova tabela `refresh_tokens` (sem RLS):
   ```sql
   create table refresh_tokens (
     id uuid primary key default gen_random_uuid(),
     tenant_id uuid references tenants(id) on delete cascade,
     user_id uuid not null references users(id) on delete cascade,
     token_hash text not null unique,
     expires_at timestamptz not null,
     revoked_at timestamptz,
     created_at timestamptz not null default now()
   );
   ```
3. Nova tabela `outbox_events` (com RLS):
   ```sql
   create table outbox_events (
     id uuid primary key default gen_random_uuid(),
     tenant_id uuid not null references tenants(id) on delete cascade,
     event_type text not null,
     payload jsonb not null default '{}'::jsonb,
     idempotency_key text not null unique,
     status text not null default 'pending'
       check (status in ('pending','processing','processed','failed')),
     attempts integer not null default 0,
     last_error text,
     created_at timestamptz not null default now(),
     processed_at timestamptz
   );
   create index idx_outbox_events_pending on outbox_events(status, created_at);
   ```
4. Após as tabelas: criar role + habilitar RLS + grants (SQL completo abaixo).

**Role e RLS (SQL exato a entra na migration, após o DDL):**

```sql
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'stockchef_app') then
    create role stockchef_app login password 'stockchef_app';
  end if;
end$$;

-- Habilita RLS + policy única em toda tabela com tenant_id (exceto tabelas de identidade)
do $$
declare
  t record;
begin
  for t in
    select c.table_name
    from information_schema.columns c
    where c.table_schema = 'public'
      and c.column_name = 'tenant_id'
      and c.table_name not in ('plans', 'tenants', 'users', 'refresh_tokens')
  loop
    execute format('alter table %I enable row level security;', t.table_name);
    execute format(
      'create policy tenant_isolation on %I using (
         tenant_id = current_setting(''app.tenant_id'', true)::uuid
       ) with check (
         tenant_id = current_setting(''app.tenant_id'', true)::uuid
       );',
      t.table_name
    );
  end loop;
end$$;

grant select, insert, update, delete on all tables in schema public to stockchef_app;
grant usage, select on all sequences in schema public to stockchef_app;
```

**Downgrade** (0001): `DROP` das tabelas na ordem reversa do DDL (lista explícita no código da migration) + `DROP ROLE IF EXISTS stockchef_app;`. Lista de tabelas para o downgrade (30+): `usage_metrics, audit_logs, recommendations, agent_runs, forecasts, inventory_count_items, inventory_counts, losses, goods_receipt_items, goods_receipts, purchase_order_items, purchase_orders, proof_of_deliveries, deliveries, payments, order_events, outbox_events, order_items, orders, drivers, zones, recipe_items, recipes, product_modifiers, products, categories, stock_movements, stock_levels, ingredients, unit_conversions, units, suppliers, customers, stores, refresh_tokens, users, subscriptions, tenants, plans`.

- [ ] **Step 1: Escrever `backend/alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url =

[loggers]
keys = root,sqlalchemy,alembic
[handlers]
keys = console
[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =
[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine
[logger_alembic]
level = INFO
handlers =
qualname = alembic
[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic
[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 2: Escrever `backend/alembic/env.py`** (lê `ALEMBIC_DATABASE_URL`; registra modelos)

```python
from __future__ import annotations

from alembic import context
from sqlalchemy import engine_from_config, pool

from app import models  # noqa: F401  (popula metadata)
from app.core.config import get_settings
from app.core.db import Base

config = context.config
if config.config_file_name is not None:
    from logging.config import fileConfig

    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().alembic_database_url)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 3: Escrever `backend/alembic/script.py.mako`** (template padrão do Alembic)
- [ ] **Step 4: Escrever `backend/alembic/versions/0001_initial.py`**

Conteúdo: arquivo único `revision = "0001"`, `down_revision = None`. Em `upgrade()`: um único `op.execute(""" <DDL do backlog :300-971 tal qual, revisado> """)` seguido de um segundo `op.execute(""" <SQL role + RLS + grants acima> """)`. Em `downgrade()`: `op.execute("DROP TABLE IF EXISTS ... CASCADE")` com a lista acima (uma linha contínua) + `op.execute("DROP ROLE IF EXISTS stockchef_app;")`.

> O executor deve copiar o DDL exato de `docs/backlog-delivery-project.md:300-971`, aplicando os deltas 1–3 (check de status, `refresh_tokens`, `outbox_events` e updates) e a seção 4 (role/RLS/grants) no final. Revisar tabela a tabela conforme risco §10 do spec.

- [ ] **Step 5: Rodar a migração no compose (validar upgrade + downgrade)**

```bash
make migrate
cd backend && ../.venv/bin/alembic downgrade base
make migrate
```

Expected: sem erro nas três execuções. Conferir tabelas: `\dt` via `docker compose exec postgres psql -U stockchef -d stockchef`.

- [ ] **Step 6: Validar RLS e role com psql (prova manual)**

```bash
docker compose exec postgres psql -U stockchef -d stockchef -c \
  "select c.table_name from information_schema.columns c
   where c.table_schema='public' and c.column_name='tenant_id'
   order by c.table_name;"
docker compose exec postgres psql -U stockchef -d stockchef -c \
  "select tablename from pg_catalog.pg_tables where schemaname='public' order by tablename;"
```

Expected: toda tabela com `tenant_id` (exceto identidade) tem policy; `stockchef_app` existe sem `rolbypassrls`; conferir `select rolbypassrls from pg_roles where rolname='stockchef_app';` → `f`. Conferir no mínimo que todas as tabelas são visíveis para dalter.

- [ ] **Step 7: Rodar a suite de integração (valida conftest + migration no testcontainer)**

```bash
cd backend && ../.venv/bin/pytest -q app/tests/integration
```

Expected: `test_health` verde — o conftest sobe Postgres 16, aplica a migration 0001 e o TestClient responde.

- [ ] **Step 8: ruff + mypy e commit**

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
git add backend && git commit -m "feat(db): migração 0001 (schema backlog + refresh_tokens/outbox + RLS + role stockchef_app)"
```

---

### Task 4: Auth multi-tenant + RLS (registro, login, refresh, isolamento)

**Files:**
- Create: `backend/app/modules/__init__.py`, `backend/app/modules/identity/__init__.py`, `backend/app/modules/identity/models.py`, `backend/app/modules/identity/security.py`, `backend/app/modules/identity/schemas.py`, `backend/app/modules/identity/routes.py`, `backend/app/core/deps.py`, `backend/app/core/tenant.py`
- Modify: `backend/app/models.py` (registrar `identity.models`), `backend/app/main.py` (incluir router de auth + middleware)

**Interfaces:**
- Preconditions: migração 0001 aplicada; `app.core.db` pronto.
- Postconditions: `POST /api/v1/auth/register|login|refresh|logout|me` funcionais (contrato abaixo); middleware injeta `request.state.actor = Actor(id, tenant_id, role)`; validação de credenciais uniforme `401 {"detail","code":"invalid_credentials"}`; divergência `X-Tenant-Id` → `403 {"code":"tenant_mismatch"}`; testes provam RLS em `stores` (e gherkin de isolamento vira teste).

**Regras de negócio:**
- Register: transação única → `tenants` (plan_id NULL, status `active`) → `set_tenant` → **`stores` "Loja principal"** → **`units` base (`kg`, `g`, `un`, `ml`, `l`)** → `users` (role `owner`, status `active`). Responde 201 com tokens (auto-login).
- Slug/email duplicados → `409 {"code":"tenant_slug_taken"|"email_taken"}`; senha mínima 8 chars (bcrypt, 72 bytes máx).
- Login: `{tenant_slug, email, password}`. Falha em qualquer etapa → mesma resposta 401 (não vaza existência). Atualiza `last_login_at`.
- Tokens: access JWT 30 min (claims `sub`, `tenant_id`, `role`); refresh 7 dias em cookie httpOnly `path=/api/v1/auth`, guardado como hash SHA-256 em `refresh_tokens`; rotação a cada uso; logout revoga.

- [ ] **Step 1: Escrever testes de auth primeiro (TDD)**

`backend/app/tests/unit/test_security.py`:

```python
from app.modules.identity.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_roundtrip() -> None:
    h = hash_password("senha-segura")
    assert h != "senha-segura"
    assert verify_password("senha-segura", h)
    assert not verify_password("errada", h)


def test_access_token_roundtrip() -> None:
    token = create_access_token(actor_id="u1", tenant_id="t1", role="owner")
    payload = decode_access_token(token)
    assert payload["sub"] == "u1"
    assert payload["tenant_id"] == "t1"
    assert payload["role"] == "owner"
```

`backend/app/tests/integration/test_auth.py`:

```python
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text as sa_text

from app.core.db import SessionLocal, set_tenant
from app.main import app


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register(client_: TestClient, slug: str, email: str) -> None:
    resp = client_.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug,
        "email": email, "password": "senha-segura", "name": "Dono",
    })
    assert resp.status_code == 201, resp.text


def _tenant_id(slug: str) -> str:
    session = SessionLocal()
    try:
        row = session.execute(sa_text("SELECT id FROM tenants WHERE slug = :s"), {"s": slug}).one()
        return str(row[0])
    finally:
        session.close()


def test_register_creates_tenant_units_and_store(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Lanches Sul", "tenant_slug": "lanches-sul",
        "email": "dono@sul.example", "password": "senha-segura", "name": "Dona",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "dono@sul.example"
    assert body["user"]["role"] == "owner"


def test_register_duplicate_slug(client: TestClient) -> None:
    _register(client, "unico", "a@b.com")
    resp = client.post("/api/v1/auth/register", json={
        "tenant_name": "Outro", "tenant_slug": "unico",
        "email": "c@d.com", "password": "senha-segura", "name": "X",
    })
    assert resp.status_code == 409
    assert resp.json()["code"] == "tenant_slug_taken"


def test_login_uniform_failure(client: TestClient) -> None:
    _register(client, "segredo", "segredo@x.com")
    for payload in (
        {"tenant_slug": "segredo", "email": "segredo@x.com", "password": "errada"},
        {"tenant_slug": "nao-existe", "email": "segredo@x.com", "password": "senha-segura"},
    ):
        resp = client.post("/api/v1/auth/login", json=payload)
        assert resp.status_code == 401, resp.text
        assert resp.json()["code"] == "invalid_credentials"


def test_refresh_rotates_and_logout_revokes(client: TestClient) -> None:
    _register(client, "rotacao", "rotacao@x.com")
    resp = client.post("/api/v1/auth/login", json={"tenant_slug": "rotacao", "email": "rotacao@x.com", "password": "senha-segura"})
    assert resp.status_code == 200
    c1 = resp.cookies["refresh_token"]
    access = resp.json()["access_token"]

    r = client.post("/api/v1/auth/refresh")
    assert r.status_code == 200
    assert r.json()["access_token"]
    assert r.cookies["refresh_token"] != c1

    r2 = client.post("/api/v1/auth/refresh")
    assert r2.status_code == 401  # cookie antigo rotacionado foi revogado

    client.headers.update({"Authorization": f"Bearer {access}"})
    assert client.get("/api/v1/auth/me").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204


def test_rls_isolation_stores(client: TestClient) -> None:
    _register(client, "pizzaria-norte", "norte@x.com")
    _register(client, "hamburgueria-sul", "sul@x.com")

    session = SessionLocal()
    try:
        set_tenant(session, _tenant_id("pizzaria-norte"))
        rows = session.execute(sa_text("SELECT name FROM stores")).all()
        assert [r[0] for r in rows] == ["Loja principal"]
    finally:
        session.close()

    session = SessionLocal()
    try:
        set_tenant(session, None)
        assert session.execute(sa_text("SELECT 1 FROM stores")).fetchall() == []
    finally:
        session.close()


def test_header_tenant_mismatch_403(client: TestClient) -> None:
    _register(client, "norte", "norte2@x.com")
    login = client.post("/api/v1/auth/login", json={"tenant_slug": "norte", "email": "norte2@x.com", "password": "senha-segura"})
    token = login.json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}", "X-Tenant-Id": str(uuid.uuid4())})
    assert resp.status_code == 403
    assert resp.json()["code"] == "tenant_mismatch"
```

> `clean_db` do conftest é autouse — cada teste roda com `tenants/plans` truncados, então os slugs podem se repetir entre testes sem colisão. O `client` fixture é function-scoped (cookiejar/headers zerados a cada teste).

- [ ] **Step 2: Criar `backend/app/modules/identity/models.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# (identity/models.py)


def _now() -> Any:
    return datetime.now(timezone.utc)


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[UUID | None] = mapped_column(ForeignKey("plans.id"), default=None)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    email: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    phone: Mapped[str | None] = mapped_column(String, default=None)
    role: Mapped[str] = mapped_column(String, default="manager")
    status: Mapped[str] = mapped_column(String, default="active")
    mfa_enabled: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

> `updated_at` sem trigger de auto-update nesta fatia (aceito; revisar nas próximas).
> IMPORTANTE: models do SQLAlchemy não incluem `tenant_id/updated_at` em todas as tabelas — apenas as colunas que a app usa; defaults python-side iguais aos do DDL.

- [ ] **Step 3: Criar `backend/app/modules/identity/security.py`**

```python
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(*, actor_id: str, tenant_id: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": actor_id,
        "tenant_id": tenant_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
```

- [ ] **Step 4: Criar `backend/app/modules/identity/schemas.py`**

```python
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=120)
    tenant_slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=120)


class LoginRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    name: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MeOut(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
```

- [ ] **Step 5: Criar `backend/app/core/tenant.py`** (middleware + Actor)

```python
from __future__ import annotations

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from uuid import UUID


class Actor(BaseModel):
    id: UUID
    tenant_id: UUID
    role: str


def install_tenant_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def tenant_scope(request: Request, call_next):
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            try:
                payload = jwt.decode(header.split(" ", 1)[1], app.state.jwt_secret, algorithms=[app.state.jwt_algorithm])
                request.state.actor = Actor(
                    id=UUID(payload["sub"]),
                    tenant_id=UUID(payload["tenant_id"]),
                    role=payload["role"],
                )
            except (jwt.PyJWTError, KeyError, TypeError, ValueError):
                return JSONResponse(status_code=401, content={"detail": "Token inválido ou expirado.", "code": "invalid_token"})
        else:
            request.state.actor = None

        actor = request.state.actor
        xt = request.headers.get("X-Tenant-Id")
        if actor is not None and xt is not None and str(actor.tenant_id) != xt:
            return JSONResponse(status_code=403, content={"detail": "Tenant do cabeçalho não confere com o token.", "code": "tenant_mismatch"})
        return await call_next(request)
```

> Gravando `jwt_secret`/`jwt_algorithm` em `app.state` no `create_app()` para o middleware não depender de import circular de settings.

- [ ] **Step 6: Criar `backend/app/core/deps.py`**

```python
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


def get_tenant_db(actor: Actor = Depends(current_actor), db: Session = Depends(get_db)) -> Iterator[Session]:
    set_tenant(db, actor.tenant_id)
    yield db
```

- [ ] **Step 7: Criar `backend/app/modules/identity/routes.py`** (fluxo completo)

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import set_tenant
from app.core.deps import current_actor, get_db
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.identity.models import RefreshToken, Tenant, User
from app.modules.identity.schemas import AuthResponse, LoginRequest, MeOut, RegisterRequest, UserOut
from app.modules.identity.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

router = APIRouter(tags=["auth"])

DEFAULT_UNITS = [
    ("kg", "Quilograma", "mass"),
    ("g", "Grama", "mass"),
    ("ml", "Mililitro", "volume"),
    ("l", "Litro", "volume"),
    ("un", "Unidade", "count"),
]


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=False,  # dev; revisar em produção
        samesite="lax",
        max_age=60 * 60 * 24 * get_settings().refresh_token_ttl_days,
        path="/api/v1/auth",
    )


def _issue_tokens(response: Response, db: Session, user: User) -> AuthResponse:
    """Grava refresh_token + commita a transação pendente e emite access+refresh."""
    access = create_access_token(actor_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
    raw = generate_refresh_token()
    db.add(RefreshToken(
        tenant_id=user.tenant_id,
        user_id=user.id,
        token_hash=hash_refresh_token(raw),
        expires_at=datetime.now(timezone.utc) + timedelta(days=get_settings().refresh_token_ttl_days),
    ))
    db.commit()
    _set_cookie(response, raw)
    return AuthResponse(access_token=access, user=UserOut.model_validate(user))


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    if db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug)):
        raise DomainError("tenant_slug_taken", "Já existe um tenant com esse slug.", status.HTTP_409_CONFLICT)

    tenant = Tenant(name=payload.tenant_name, slug=payload.tenant_slug, status="active")
    db.add(tenant)
    db.flush()
    set_tenant(db, tenant.id)

    db.add(Store(tenant_id=tenant.id, name="Loja principal", status="active"))
    for symbol, name, typ in DEFAULT_UNITS:
        db.add(Unit(tenant_id=tenant.id, name=name, symbol=symbol, type=typ))

    user = User(
        tenant_id=tenant.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="owner",
        status="active",
    )
    db.add(user)
    db.flush()

    return _issue_tokens(response, db, user)


@router.post("/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == payload.tenant_slug))
    user = db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == payload.email)) if tenant else None
    if user is None or not verify_password(payload.password, user.password_hash):
        raise DomainError("invalid_credentials", "Credenciais inválidas.", status.HTTP_401_UNAUTHORIZED)
    user.last_login_at = datetime.now(timezone.utc)
    return _issue_tokens(response, db, user)
```

- [ ] **Step 8: Endpoints restantes (refresh/logout/me) — arquivo continua**

```python
@router.post("/refresh")
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> AuthResponse:
    raw = request.cookies.get("refresh_token")
    if not raw:
        raise DomainError("invalid_token", "Sessão ausente.", status.HTTP_401_UNAUTHORIZED)
    tok = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(raw),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    if tok is None:
        raise DomainError("invalid_token", "Sessão expirada ou inválida.", status.HTTP_401_UNAUTHORIZED)

    tok.revoked_at = datetime.now(timezone.utc)
    user = db.get(User, tok.user_id)
    if user is None:
        raise DomainError("invalid_token", "Sessão expirada ou inválida.", status.HTTP_401_UNAUTHORIZED)

    return _issue_tokens(response, db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    raw = request.cookies.get("refresh_token")
    if raw:
        tok = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw)))
        if tok is not None:
            tok.revoked_at = datetime.now(timezone.utc)
            db.commit()
    response.delete_cookie("refresh_token", path="/api/v1/auth")


@router.get("/me")
def me(actor: Actor = Depends(current_actor), db: Session = Depends(get_db)) -> MeOut:
    tenant = db.get(Tenant, actor.tenant_id)
    user = db.get(User, actor.id)
    if tenant is None or user is None:
        raise DomainError("unauthorized", "Sessão inválida.", status.HTTP_401_UNAUTHORIZED)
    return MeOut(id=user.id, name=user.name, email=user.email, role=user.role,
                 tenant_id=tenant.id, tenant_name=tenant.name, tenant_slug=tenant.slug)
```

> O `register` acima já usa `Store`/`Unit` (criados no Step 9 deste Task) — não há `_DefaultStore`/`_Unit` no código final. O DDL das tabelas vem do backlog; os models de stores/units começam mínimos e crescem nas Tasks 5–7.

- [ ] **Step 9: Criar `backend/app/modules/catalog/__init__.py` (+ models mínimos de stores/units), registrar tudo e ligar no app**

`backend/app/modules/catalog/models.py` (mínimo para register):

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(timezone.utc)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="count")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

`backend/app/models.py`:

```python
"""Registro central de modelos — cada módulo importado aqui popula o metadata."""
from app.core.db import Base as Base
from app.modules.catalog.models import Store, Unit  # noqa: F401
from app.modules.identity.models import RefreshToken, Tenant, User  # noqa: F401

metadata = Base.metadata
```

`backend/app/main.py` (editar):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.api import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.tenant import install_tenant_middleware
from app.modules.identity.routes import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="StockChef API", version="0.1.0", lifespan=lifespan)
    app.state.jwt_secret = get_settings().jwt_secret
    app.state.jwt_algorithm = get_settings().jwt_algorithm
    register_exception_handlers(app)
    install_tenant_middleware(app)

    @api_router.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    app.include_router(auth_router, prefix="/api/v1/auth")
    return app


app = create_app()
```

- [ ] **Step 10: Rodar suite (TDD — error primeiro, depois verde)**

```bash
cd backend
../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/unit/test_security.py app/tests/integration/test_auth.py
```

Expected: testes verdes após implementação (primeiro rodam e falham por ausência dos símbolos — seguir TDD: escrever → vermelho → implementar → verde).

- [ ] **Step 11: Commit**

```bash
git add backend/app
git commit -m "feat(auth): registro/login/refresh/logout/me multi-tenant + RLS provado em testes"
```

---

### Task 5: Insumos + unidades (auto-create) + estoque inicial

**Files:**
- Modify: `backend/app/modules/catalog/models.py` (ingredients, stock_levels, stock_movements), `backend/app/models.py` (registro), `backend/app/main.py`
- Create: `backend/app/modules/catalog/schemas.py`, `backend/app/modules/catalog/routes.py`, `backend/app/tests/integration/test_insumos.py`

**Interfaces:**
- Preconditions: auth + RLS funcionais (Task 4).
- Postconditions: `GET/POST /api/v1/insumos`, `PATCH /api/v1/insumos/{id}` autenticados; unidade auto-create por `base_unit_symbol` (por tenant); `initial_stock` grava `stock_levels` na loja padrão (default = primeira loja `active` do tenant); listagem retorna `stock_total`.

**Contrato:**
- `POST /insumos` body: `{"name", "category"?, "base_unit_symbol", "average_cost", "minimum_stock"?=0, "initial_stock"?=0}` → 201 `IngredientOut {id, name, category, base_unit:{id,symbol}, average_cost, minimum_stock, stock_total}`.
- `GET /insumos` → `[{IngredientOut...}]` (RLS filtra por tenant no banco; sem paginação nesta fatia).
- `PATCH /insumos/{id}` body parcial `{"name"?, "category"?, "average_cost"?, "minimum_stock"?}`; ao alterar `average_cost`, propaga para `stock_levels.average_cost` vigente.
- Decimals saem como string no JSON (comportamento padrão do Pydantic v2); frontend converte com `Number()`.

- [ ] **Step 1: Testes de insumos primeiro (TDD)**

`backend/app/tests/integration/test_insumos.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _auth_headers(slug: str, email: str = "dono@x.com") -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": email,
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_insumo_with_initial_stock() -> None:
    h = _auth_headers("queijaria")
    resp = client.post("/api/v1/insumos", headers=h, json={
        "name": "Queijo cheddar", "base_unit_symbol": "kg",
        "average_cost": "45.00", "initial_stock": "3.00",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Queijo cheddar"
    assert body["base_unit"]["symbol"] == "kg"
    assert body["average_cost"] == "45.00"
    assert body["stock_total"] == "3.00"


def test_unit_is_reused_per_tenant() -> None:
    h = _auth_headers("unidades")
    r1 = client.post("/api/v1/insumos", headers=h, json={"name": "A", "base_unit_symbol": "kg", "average_cost": "1"})
    r2 = client.post("/api/v1/insumos", headers=h, json={"name": "B", "base_unit_symbol": "kg", "average_cost": "2"})
    assert r1.json()["base_unit"]["id"] == r2.json()["base_unit"]["id"]


def test_patch_average_cost_propagates() -> None:
    h = _auth_headers("precos")
    r = client.post("/api/v1/insumos", headers=h, json={"name": "Pão", "base_unit_symbol": "un", "average_cost": "1.00", "initial_stock": "10"})
    insumo_id = r.json()["id"]
    resp = client.patch(f"/api/v1/insumos/{insumo_id}", headers=h, json={"average_cost": "1.50"})
    assert resp.status_code == 200
    assert resp.json()["average_cost"] == "1.50"


def test_list_is_isolated_per_tenant() -> None:
    h_a = _auth_headers("ins-a")
    h_b = _auth_headers("ins-b", email="b@x.com")
    client.post("/api/v1/insumos", headers=h_a, json={"name": "Alface", "base_unit_symbol": "un", "average_cost": "0.5"})
    lista = client.get("/api/v1/insumos", headers=h_b).json()
    assert lista == []
```

- [ ] **Step 2: Estender `catalog/models.py`**

```python
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    category: Mapped[str | None] = mapped_column(String, default=None)
    base_unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    default_supplier_id: Mapped[UUID | None] = mapped_column(ForeignKey("suppliers.id"), default=None)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    maximum_stock: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StockLevel(Base):
    __tablename__ = "stock_levels"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    average_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    last_counted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    reference_type: Mapped[str | None] = mapped_column(String, default=None)
    reference_id: Mapped[UUID | None] = mapped_column(default=None)
    reason: Mapped[str | None] = mapped_column(String, default=None)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, default=None)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 3: Criar `schemas.py`**

```python
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class UnitOut(BaseModel):
    id: UUID
    symbol: str


class IngredientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: str | None = None
    base_unit_symbol: str = Field(min_length=1, max_length=20)
    average_cost: Decimal = Field(default=Decimal("0"), ge=0)
    minimum_stock: Decimal = Field(default=Decimal("0"), ge=0)
    initial_stock: Decimal = Field(default=Decimal("0"), ge=0)


class IngredientPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    average_cost: Decimal | None = Field(default=None, ge=0)
    minimum_stock: Decimal | None = Field(default=None, ge=0)


class IngredientOut(BaseModel):
    id: UUID
    name: str
    category: str | None
    base_unit: UnitOut
    average_cost: Decimal
    minimum_stock: Decimal
    status: str
    stock_total: Decimal
```

- [ ] **Step 4: Helpers `catalog/service.py` (unidade auto-create + stock)**

`backend/app/modules/catalog/service.py`:

```python
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import Ingredient, StockLevel, Store, Unit

SYMBOL_TYPE = {"kg": "mass", "g": "mass", "ml": "volume", "l": "volume", "un": "count"}


def get_or_create_unit(db: Session, tenant_id: UUID, symbol: str) -> Unit:
    unit = db.scalar(select(Unit).where(Unit.tenant_id == tenant_id, Unit.symbol == symbol))
    if unit is None:
        unit = Unit(tenant_id=tenant_id, name=symbol, symbol=symbol, type=SYMBOL_TYPE.get(symbol, "other"))
        db.add(unit)
        db.flush()
    return unit


def default_store(db: Session, tenant_id: UUID) -> Store:
    store = db.scalar(
        select(Store).where(Store.tenant_id == tenant_id, Store.status == "active").order_by(Store.created_at).limit(1)
    )
    if store is None:
        raise DomainError("no_store", "Nenhuma loja ativa para o tenant.")
    return store


def stock_total(db: Session, ingredient_id: UUID) -> Decimal:
    total = db.scalar(
        select(StockLevel.quantity).where(StockLevel.ingredient_id == ingredient_id)
    )
    return total or Decimal("0")
```

- [ ] **Step 5: Criar `catalog/routes.py`**

```python
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.models import Ingredient, StockLevel
from app.modules.catalog.schemas import IngredientCreate, IngredientOut, IngredientPatch, UnitOut
from app.modules.catalog.service import default_store, get_or_create_unit, stock_total

router = APIRouter(tags=["insumos"])


def _tenant_id(db: Session) -> UUID:
    """Tenant ativo da sessão — setado por get_tenant_db (app.core.deps)."""
    return db.info["tenant_id"]


def _to_out(db: Session, ing: Ingredient) -> IngredientOut:
    from app.modules.catalog.models import Unit
    unit = db.get(Unit, ing.base_unit_id)
    return IngredientOut(
        id=ing.id, name=ing.name, category=ing.category,
        base_unit=UnitOut(id=unit.id, symbol=unit.symbol),
        average_cost=ing.average_cost, minimum_stock=ing.minimum_stock,
        status=ing.status, stock_total=stock_total(db, ing.id),
    )


@router.post("/insumos", status_code=status.HTTP_201_CREATED)
def create_insumo(payload: IngredientCreate, db: Session = Depends(get_tenant_db)) -> IngredientOut:
    if db.scalar(select(Ingredient).where(Ingredient.tenant_id == _tenant_id(db), Ingredient.name == payload.name)):
        raise DomainError("insumo_exists", "Já existe um insumo com esse nome.", status.HTTP_409_CONFLICT)
    unit = get_or_create_unit(db, _tenant_id(db), payload.base_unit_symbol)
    ing = Ingredient(
        tenant_id=_tenant_id(db), name=payload.name, category=payload.category,
        base_unit_id=unit.id, average_cost=payload.average_cost,
        minimum_stock=payload.minimum_stock, status="active",
    )
    db.add(ing)
    db.flush()
    if payload.initial_stock > 0:
        store = default_store(db, _tenant_id(db))
        db.add(StockLevel(
            tenant_id=_tenant_id(db), store_id=store.id, ingredient_id=ing.id,
            quantity=payload.initial_stock, average_cost=payload.average_cost,
        ))
    db.commit()
    return _to_out(db, ing)


@router.get("/insumos")
def list_insumos(db: Session = Depends(get_tenant_db)) -> list[IngredientOut]:
    ings = db.scalars(
        select(Ingredient).where(Ingredient.tenant_id == _tenant_id(db), Ingredient.status != "archived")
        .order_by(Ingredient.name)
    ).all()
    return [_to_out(db, i) for i in ings]


@router.patch("/insumos/{insumo_id}")
def patch_insumo(insumo_id: UUID, payload: IngredientPatch, db: Session = Depends(get_tenant_db)) -> IngredientOut:
    ing = db.get(Ingredient, insumo_id)
    if ing is None:
        raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
    for field in ("name", "category", "minimum_stock"):
        value = getattr(payload, field)
        if value is not None:
            setattr(ing, field, value)
    if payload.average_cost is not None:
        ing.average_cost = payload.average_cost
        db.execute(update(StockLevel).where(StockLevel.ingredient_id == insumo_id).values(average_cost=payload.average_cost))
    db.commit()
    return _to_out(db, ing)
```

- [ ] **Step 6: Registrar `models`/`routes` e rodar**

`backend/app/models.py` adicionar: `from app.modules.catalog.models import Ingredient, StockLevel, StockMovement, Store, Unit  # noqa: F401`.

`backend/app/main.py` adicionar: `from app.modules.catalog.routes import router as catalog_router` e `app.include_router(catalog_router, prefix="/api/v1")`.

Run:

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/integration/test_insumos.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/app && git commit -m "feat(catalog): insumos com unidade auto-create e saldo inicial"
```

---

### Task 6: Produtos + ficha técnica + cálculo de custo (Gherkin X-Burger)

**Files:**
- Modify: `backend/app/modules/catalog/models.py` (products, recipes, recipe_items), `backend/app/models.py`, `backend/app/main.py`
- Create: `backend/app/modules/catalog/costing.py`, `backend/app/tests/unit/test_costing.py`, `backend/app/tests/integration/test_produtos.py`

**Interfaces:**
- Preconditions: insumos funcionais (Task 5).
- Postconditions: `GET/POST /api/v1/produtos`; `GET/POST /api/v1/produtos/{id}/ficha-tecnica`. Ficha sempre na unidade-base do insumo (sem conversão, API não recebe `unit_id`); `waste_factor` ignorado. Ao salvar a ficha, o custo do produto é recalcular no GET de ficha/margem — nada é persistido em coluna (o DDL de `products` não tem custo).

**Regras:**
- `POST /produtos` body: `{"name", "price", "store_id"?, "description"?, "preparation_time_minutes"?=10}` → 201. Cria `recipes` version 1 status `draft` vazio (ficha nasce na Task: POST ficha o promove para `active`).
- `POST /produtos/{id}/ficha-tecnica` body: `{"items": [{"ingredient_id", "quantity"}]}` → substitui os itens da ficha ativa (cria versão `active` se não existir). Valida: insumo existe; `quantity > 0`. Responde a ficha com `cost` por item + `total_cost`.
- `GET /produtos/{id}/ficha-tecnica` → `{product_id, status, version, items: [{ingredient_id, name, unit_symbol, quantity, cost}], total_cost}`.
- `costing.py`: `ingredient_cost(qty, avg) = round2(qty*avg)`; `recipe_cost(items)` soma. Gherkin: `0.030 kg × 45.00 = 1.35`.

- [ ] **Step 1: Testes primeiro (TDD)**

`backend/app/tests/unit/test_costing.py`:

```python
from decimal import Decimal

from app.modules.catalog.costing import ingredient_cost, recipe_cost


def test_xburger_queijo_cheddar() -> None:
    assert ingredient_cost(Decimal("0.030"), Decimal("45.00")) == Decimal("1.35")


def test_recipe_cost_sums_items() -> None:
    assert recipe_cost([(Decimal("0.030"), Decimal("45.00")), (Decimal("2"), Decimal("1.00"))]) == Decimal("3.35")
```

`backend/app/tests/integration/test_produtos.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _insumo(h: dict[str, str], name: str, avg: str, unit: str = "kg", stock: str = "0") -> str:
    r = client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": unit, "average_cost": avg, "initial_stock": stock,
    })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_create_product_and_recipe_cost() -> None:
    h = _setup("burguer")
    queijo = _insumo(h, "Queijo cheddar", "45.00", "kg", "3.00")
    pao = _insumo(h, "Pão brioche", "2.00", "un", "50")
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "20.00"})
    assert p.status_code == 201, p.text
    pid = p.json()["id"]

    resp = client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": queijo, "quantity": "0.030"}, {"ingredient_id": pao, "quantity": "2"}],
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "active"
    assert body["total_cost"] == "3.35"

    ficha = client.get(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h).json()
    queijo_item = next(i for i in ficha["items"] if i["name"] == "Queijo cheddar")
    assert queijo_item["cost"] == "1.35"


def test_ficha_replaces_items() -> None:
    h = _setup("burger2")
    queijo = _insumo(h, "Queijo", "45.00", "kg")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "X", "price": "10"}).json()["id"]
    client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": [{"ingredient_id": queijo, "quantity": "0.020"}]})
    resp = client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": [{"ingredient_id": queijo, "quantity": "0.040"}]})
    assert len(resp.json()["items"]) == 1
    assert resp.json()["total_cost"] == "1.80"


def test_ficha_unknown_ingredient_404() -> None:
    import uuid
    h = _setup("burger3")
    pid = client.post("/api/v1/produtos", headers=h, json={"name": "Y", "price": "10"}).json()["id"]
    resp = client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": [{"ingredient_id": str(uuid.uuid4()), "quantity": "1"}]})
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_found"
```

- [ ] **Step 2: Estender `catalog/models.py` (products, recipes, recipe_items)**

```python
class Product(Base):
    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(ForeignKey("categories.id"), default=None)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(String, default=None)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    stock_control_enabled: Mapped[bool] = mapped_column(default=True)
    preparation_time_minutes: Mapped[int] = mapped_column(default=10)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[str] = mapped_column(String, default="draft")
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    created_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RecipeItem(Base):
    __tablename__ = "recipe_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    recipe_id: Mapped[UUID] = mapped_column(ForeignKey("recipes.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    unit_id: Mapped[UUID] = mapped_column(ForeignKey("units.id"), nullable=False)
    waste_factor: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0"))
    optional: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 3: Criar `costing.py`**

```python
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def ingredient_cost(quantity: Decimal, average_cost: Decimal) -> Decimal:
    return (quantity * average_cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def recipe_cost(quantities_costs: list[tuple[Decimal, Decimal]]) -> Decimal:
    total = sum((ingredient_cost(q, c) for q, c in quantities_costs), Decimal("0"))
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
```

- [ ] **Step 4: Schemas (append em `catalog/schemas.py`)**

```python
class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(ge=0)
    store_id: UUID | None = None
    description: str | None = None
    preparation_time_minutes: int = Field(default=10, ge=0)


class ProductOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: Decimal
    active: bool
    preparation_time_minutes: int


class RecipeItemIn(BaseModel):
    ingredient_id: UUID
    quantity: Decimal = Field(gt=0)


class RecipeSetIn(BaseModel):
    items: list[RecipeItemIn]


class RecipeItemOut(BaseModel):
    ingredient_id: UUID
    name: str
    unit_symbol: str
    quantity: Decimal
    cost: Decimal


class RecipeOut(BaseModel):
    product_id: UUID
    status: str
    version: int
    items: list[RecipeItemOut]
    total_cost: Decimal
```

- [ ] **Step 5: Rotas de produtos + ficha (append em `catalog/routes.py`)**

```python
@router.post("/produtos", status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_tenant_db)) -> ProductOut:
    tid = _tenant_id(db)
    if db.scalar(select(Product).where(Product.tenant_id == tid, Product.name == payload.name)):
        raise DomainError("product_exists", "Já existe um produto com esse nome.", status.HTTP_409_CONFLICT)
    store = payload.store_id or default_store(db, tid).id
    product = Product(tenant_id=tid, store_id=store, name=payload.name, price=payload.price,
                      description=payload.description, preparation_time_minutes=payload.preparation_time_minutes)
    db.add(product)
    db.flush()
    db.add(Recipe(tenant_id=tid, product_id=product.id, version=1, status="draft"))
    db.commit()
    return ProductOut.model_validate(product)


@router.get("/produtos")
def list_produtos(db: Session = Depends(get_tenant_db)) -> list[ProductOut]:
    rows = db.scalars(select(Product).where(Product.tenant_id == _tenant_id(db)).order_by(Product.name)).all()
    return [ProductOut.model_validate(p) for p in rows]


def _active_recipe_or_create(db: Session, tid: UUID, product_id: UUID) -> Recipe:
    recipe = db.scalar(select(Recipe).where(Recipe.product_id == product_id, Recipe.status == "active").order_by(Recipe.version.desc()).limit(1))
    if recipe is None:
        draft = db.scalar(select(Recipe).where(Recipe.product_id == product_id, Recipe.status == "draft").order_by(Recipe.version.desc()).limit(1))
        if draft is not None:
            draft.status = "active"
            recipe = draft
        else:
            maxv = db.scalar(select(func.max(Recipe.version)).where(Recipe.product_id == product_id)) or 0
            recipe = Recipe(tenant_id=tid, product_id=product_id, version=maxv + 1, status="active")
            db.add(recipe)
    return recipe


@router.post("/produtos/{product_id}/ficha-tecnica")
def set_ficha(product_id: UUID, payload: RecipeSetIn, db: Session = Depends(get_tenant_db)) -> RecipeOut:
    tid = _tenant_id(db)
    if db.get(Product, product_id) is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    recipe = _active_recipe_or_create(db, tid, product_id)
    db.query(RecipeItem).filter(RecipeItem.recipe_id == recipe.id).delete()
    items: list[RecipeItem] = []
    for it in payload.items:
        ing = db.get(Ingredient, it.ingredient_id)
        if ing is None:
            raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
        items.append(RecipeItem(tenant_id=tid, recipe_id=recipe.id, ingredient_id=ing.id,
                                quantity=it.quantity, unit_id=ing.base_unit_id))
    db.add_all(items)
    db.flush()
    db.commit()
    return _build_recipe_out(db, recipe)


@router.get("/produtos/{product_id}/ficha-tecnica")
def get_ficha(product_id: UUID, db: Session = Depends(get_tenant_db)) -> RecipeOut:
    recipe = db.scalar(select(Recipe).where(Recipe.product_id == product_id).order_by(Recipe.version.desc()).limit(1))
    if recipe is None:
        raise DomainError("not_found", "Produto sem ficha técnica.", status.HTTP_404_NOT_FOUND)
    return _build_recipe_out(db, recipe)


def _build_recipe_out(db: Session, recipe: Recipe) -> RecipeOut:
    items = db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all()
    out_items: list[RecipeItemOut] = []
    for it in items:
        ing = db.get(Ingredient, it.ingredient_id)
        unit = db.get(Unit, it.unit_id)
        out_items.append(RecipeItemOut(
            ingredient_id=it.ingredient_id, name=ing.name, unit_symbol=unit.symbol,
            quantity=it.quantity, cost=ingredient_cost(it.quantity, ing.average_cost),
        ))
    return RecipeOut(product_id=recipe.product_id, status=recipe.status, version=recipe.version,
                     items=out_items, total_cost=recipe_cost([(i.quantity, db.get(Ingredient, i.ingredient_id).average_cost) for i in items]))
```

- [ ] **Step 6: Registrar e rodar**

`models.py` (registro de Product/Recipe/RecipeItem), `main.py` já inclui `catalog_router`.

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/unit/test_costing.py app/tests/integration/test_produtos.py
```

Expected: verde (TDD: vermelho primeiro).

- [ ] **Step 7: Commit**

```bash
git add backend/app && git commit -m "feat(catalog): produtos + ficha técnica com custo (gherkin X-Burger)"
```

---

### Task 7: Criação de pedidos + validação de disponibilidade

**Files:**
- Create: `backend/app/modules/orders/__init__.py`, `backend/app/modules/orders/models.py`, `backend/app/modules/orders/schemas.py`, `backend/app/modules/orders/service.py`, `backend/app/modules/orders/routes.py`, `backend/app/tests/integration/test_pedidos.py`
- Modify: `backend/app/models.py`, `backend/app/main.py`

**Interfaces:**
- Preconditions: catálogo completo (Task 6); estoque em `stock_levels`.
- Postconditions: `POST /api/v1/pedidos`, `GET /api/v1/pedidos`, `GET /api/v1/pedidos/{id}`. Criação valida disponibilidade → `422 {"detail","code":"insufficient_stock","missing":[...]}` (spec §6.5). `order_items.recipe_snapshot` captura a ficha ativa no momento da criação (baixa futura usa o snapshot, não a receita viva).

**Regras:**
- Body: `{"store_id"?, "customer_name"?, "customer_phone"?, "items": [{"product_id","quantity"}], "notes"?, "fulfillment_type"?="delivery", "channel"?="own_pwa"}`.
- Loja: default do tenant (como insumos). Item: `unit_price = product.price`, `total_price = unit_price × quantity`; `subtotal = total = Σ total_price` (sem fee/desconto/taxa).
- Produto sem ficha ativa → `422 {"code":"recipe_missing"}`.
- Disponibilidade: `Σ (item.quantity × ficha.quantity)` por insumo; exigência `> estoque` → `422` com lista `missing`; sem baixa (a transação de criação é descartada).
- `code` do pedido: `SC-<8 hex>`; único por (tenant, store).
- `status` inicial = `received`. Cliente:
  `customer_phone` informado → upsert por (tenant, phone) em `customers`; senão `customer_id = NULL`.

- [ ] **Step 1: Testes primeiro (TDD)**

`backend/app/tests/integration/test_pedidos.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _ingredient(h, name, avg, stock) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={"name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _product(h, name, price, ficha: list[tuple[str, str]]) -> str:
    r = client.post("/api/v1/produtos", headers=h, json={"name": name, "price": price})
    pid = r.json()["id"]
    client.post(f"/api/v1/produtos/{pid}/ficha-tecnica", headers=h, json={"items": [{"ingredient_id": i, "quantity": q} for i, q in ficha]})
    return pid


def _order(h, product_id: str, qty: int) -> object:
    return client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": product_id, "quantity": qty}]})


def test_create_order_with_stock() -> None:
    h = _setup("pedido1")
    queijo = _ingredient(h, "Queijo", "45.00", "3.00")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    resp = _order(h, pid, 2)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "received"
    assert body["total"] == "40.00"
    assert body["code"].startswith("SC-")
    assert len(body["order_items"]) == 1


def test_create_order_insufficient_stock_422() -> None:
    h = _setup("pedido2")
    queijo = _ingredient(h, "Queijo", "45.00", "0.050")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    resp = _order(h, pid, 2)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "insufficient_stock"
    assert body["missing"][0]["required"] == "0.060"


def test_create_order_recipe_missing_422() -> None:
    h = _setup("pedido3")
    r = client.post("/api/v1/produtos", headers=h, json={"name": "Sem Ficha", "price": "10"})
    pid = r.json()["id"]
    resp = _order(h, pid, 1)
    assert resp.status_code == 422
    assert resp.json()["code"] == "recipe_missing"


def test_list_orders_scoped() -> None:
    h = _setup("pedido4")
    queijo = _ingredient(h, "Queijo", "45.00", "3.00")
    pid = _product(h, "X-Burger", "20.00", [(queijo, "0.030")])
    _order(h, pid, 1)
    lista = client.get("/api/v1/pedidos", headers=h)
    assert lista.status_code == 200
    assert len(lista.json()) == 1
```

- [ ] **Step 2: Criar `orders/models.py`**

```python
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(timezone.utc)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    customer_id: Mapped[UUID | None] = mapped_column(ForeignKey("customers.id"), default=None)
    code: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="received")
    channel: Mapped[str] = mapped_column(String, default="own_pwa")
    fulfillment_type: Mapped[str] = mapped_column(String, default="delivery")
    subtotal: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    discount_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    modifiers: Mapped[dict] = mapped_column(JSONB, default=dict)
    notes: Mapped[str | None] = mapped_column(String, default=None)
    recipe_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String)
    from_status: Mapped[str | None] = mapped_column(String, default=None)
    to_status: Mapped[str | None] = mapped_column(String, default=None)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    idempotency_key: Mapped[str] = mapped_column(String, unique=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str | None] = mapped_column(String, default=None)
    phone: Mapped[str | None] = mapped_column(String, default=None)
    email: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 3: Schemas de pedidos**

```python
class OrderItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    store_id: UUID | None = None
    customer_name: str | None = None
    customer_phone: str | None = None
    items: list[OrderItemRequest] = Field(min_length=1)
    notes: str | None = None
    fulfillment_type: str = "delivery"
    channel: str = "own_pwa"


class OrderItemOut(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class OrderOut(BaseModel):
    id: UUID
    code: str
    status: str
    customer_name: str | None
    customer_phone: str | None
    subtotal: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    order_items: list[OrderItemOut]
```

- [ ] **Step 4: Criar `orders/service.py` (disponibilidade + snapshot + totais)**

```python
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import Product, Recipe, RecipeItem, StockLevel
from app.modules.orders.models import Order

MISSING_HTTP = 422


def load_active_recipe(db: Session, product_id: UUID) -> Recipe:
    recipe = db.scalar(
        select(Recipe).where(Recipe.product_id == product_id, Recipe.status == "active").order_by(Recipe.version.desc()).limit(1)
    )
    if recipe is None:
        raise DomainError("recipe_missing", "Produto sem ficha técnica ativa.", MISSING_HTTP)
    return recipe


def availability(db: Session, tid: UUID, store_id: UUID, items: list[tuple[UUID, int]]) -> None:
    """Eleva 422 se algum insumo ficar aquém do exigido."""
    required: defaultdict[UUID, Decimal] = defaultdict(Decimal)
    for product_id, qty in items:
        recipe = load_active_recipe(db, product_id)
        for it in db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all():
            required[it.ingredient_id] += it.quantity * qty

    missing = []
    for ingredient_id, need in required.items():
        have = db.scalar(
            select(StockLevel.quantity).where(StockLevel.store_id == store_id, StockLevel.ingredient_id == ingredient_id)
        ) or Decimal("0")
        if need > have:
            missing.append({"ingredient_id": str(ingredient_id), "required": str(need), "available": str(have)})
    if missing:
        raise DomainError("insufficient_stock", "Estoque insuficiente para o pedido.", MISSING_HTTP, extra={"missing": missing})


def recipe_snapshot(db: Session, product_id: UUID) -> list[dict]:
    recipe = load_active_recipe(db, product_id)
    return [{"ingredient_id": str(it.ingredient_id), "quantity": str(it.quantity), "unit_id": str(it.unit_id)}
            for it in db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all()]
```
```

- [ ] **Step 5: Rotas de pedidos**

```python
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db
from app.core.errors import DomainError
from app.modules.catalog.models import Product
from app.modules.catalog.service import default_store
from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem
from app.modules.orders.schemas import OrderCreate, OrderItemOut, OrderOut
from app.modules.orders.service import availability, recipe_snapshot

router = APIRouter(tags=["pedidos"])


def _gen_code(db: Session, store_id: UUID) -> str:
    import secrets
    return f"SC-{secrets.token_hex(4).upper()}"


def _upsert_customer(db: Session, tid: UUID, name: str | None, phone: str | None) -> Customer | None:
    if not phone and not name:
        return None
    if phone:
        cust = db.scalar(select(Customer).where(Customer.tenant_id == tid, Customer.phone == phone))
        if cust is not None:
            if name:
                cust.name = name
            return cust
    cust = Customer(tenant_id=tid, name=name, phone=phone)
    db.add(cust)
    db.flush()
    return cust


def _to_out(db: Session, order: Order) -> OrderOut:
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    out_items = []
    for it in items:
        product = db.get(Product, it.product_id)
        out_items.append(OrderItemOut(product_id=it.product_id, product_name=product.name,
                                      quantity=it.quantity, unit_price=it.unit_price, total_price=it.total_price))
    cust = db.get(Customer, order.customer_id) if order.customer_id else None
    return OrderOut(
        id=order.id, code=order.code, status=order.status,
        customer_name=cust.name if cust else None, customer_phone=cust.phone if cust else None,
        subtotal=order.subtotal, total=order.total, notes=order.notes,
        created_at=order.created_at, order_items=out_items,
    )


@router.post("/pedidos", status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreate, db: Session = Depends(get_tenant_db)) -> OrderOut:
    tid = _tenant_id(db)
    store_id = payload.store_id or default_store(db, tid).id
    availability(db, tid, store_id, [(it.product_id, it.quantity) for it in payload.items])

    customer = _upsert_customer(db, tid, payload.customer_name, payload.customer_phone)
    order = Order(tenant_id=tid, store_id=store_id, customer_id=customer.id if customer else None,
                  code=_gen_code(db, store_id), status="received",
                  channel=payload.channel, fulfillment_type=payload.fulfillment_type,
                  notes=payload.notes)
    db.add(order)
    db.flush()

    subtotal = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        unit_price = product.price
        total_price = unit_price * it.quantity
        subtotal += total_price
        db.add(OrderItem(tenant_id=tid, order_id=order.id, product_id=it.product_id, quantity=it.quantity,
                         unit_price=unit_price, total_price=total_price, recipe_snapshot=recipe_snapshot(db, it.product_id)))
    order.subtotal = subtotal
    order.total = subtotal
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="order.created", from_status=None, to_status="received"))
    db.commit()
    return _to_out(db, order)


@router.get("/pedidos")
def list_orders(db: Session = Depends(get_tenant_db)) -> list[OrderOut]:
    rows = db.scalars(select(Order).where(Order.tenant_id == _tenant_id(db)).order_by(Order.created_at.desc())).all()
    return [_to_out(db, o) for o in rows]


@router.get("/pedidos/{order_id}")
def get_order(order_id: UUID, db: Session = Depends(get_tenant_db)) -> OrderOut:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    return _to_out(db, order)
```

- [ ] **Step 6: Registrar e rodar**

`models.py`: registrar `Customer, Order, OrderItem, OrderEvent, OutboxEvent`. `main.py`: `orders_router` com prefix `/api/v1`. `DomainError` já aceita `extra` (Task 2) — o `422` de `availability` propaga `missing`.

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/integration/test_pedidos.py
```

- [ ] **Step 7: Commit**

```bash
git add backend/app && git commit -m "feat(orders): criação de pedidos com validação de estoque e snapshot de ficha"
```

---

### Task 8: Confirmação + outbox + baixa idempotente (Gherkin baixa automática)

**Files:**
- Create: `backend/app/modules/orders/outbox.py`, `backend/app/tests/integration/test_confirmacao.py`
- Modify: `backend/app/modules/orders/routes.py` (`/pedidos/{id}/confirmar`, `/pedidos/{id}/eventos`), `backend/app/modules/orders/service.py` (helper `availability_ok`; remover param `tid` ocioso de `availability`)

**Interfaces:**
- Preconditions: pedidos com snapshot (Task 7).
- Postconditions: confirmação transacional → `order_events` + `outbox_events` (`order.confirmed`) + worker in-process pós-commit drena a outbox: decremento atômico + `stock_movements` (`sale`, `idempotency_key = "order.confirmed:{order_id}:{ingredient_id}"`). Repetir confirmação e reprocessar outbox é no-op. Saldo insuficiente → `confirmed_pending_stock` + outbox `failed`, sem baixa parcial.

**Decisões de implementação:**
- Worker usa `BackgroundTasks` do Starlette (não `asyncio.create_task`): roda pós-commit **dentro** do ciclo ASGI → determinístico sob `TestClient`; mesma abstração de "worker in-process". RabbitMQ/worker dedicado continua como Fase 2.
- `confirmar` não bloqueia venda (spec §6.3): disponibilidade verificada, mas insuficiência vira `confirmed_pending_stock` (nunca 422).
- `drain_outbox` lê eventos `pending` de um tenant, processa cada um em transação própria. Idempotência dupla: (1) movimentos pré-existentes por `reference_type='order'` fazem reprocessar virar no-op; (2) `idempotency_key` unique na tabela barra duplicidade (defesa extra).
- Movimentação de `sale` usa `quantity` **negativo** com `unit_cost` = custo médio vigente.

- [ ] **Step 1: Testes primeiro (TDD)**

`backend/app/tests/integration/test_confirmacao.py`:

```python
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import SessionLocal, set_tenant
from app.main import app
from app.modules.catalog.models import StockLevel
from app.modules.identity.models import Tenant

client = TestClient(app)


def _setup(slug: str) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, _tenant_id(slug)


def _tenant_id(slug: str) -> str:
    db = SessionLocal()
    try:
        return str(db.scalar(select(Tenant.id).where(Tenant.slug == slug)))
    finally:
        db.close()


def _ingredient(h, name, avg, stock) -> str:
    r = client.post("/api/v1/insumos", headers=h, json={"name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock})
    return r.json()["id"]


def _xburger(h, queijo: str) -> str:
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "20.00"}).json()["id"]
    client.post(f"/api/v1/produtos/{p}/ficha-tecnica", headers=h, json={"items": [{"ingredient_id": queijo, "quantity": "0.030"}]})
    return p


def _stock(ingredient_id: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tenant_id(slug))
        return str(db.scalar(select(StockLevel.quantity).where(StockLevel.ingredient_id == ingredient_id)))
    finally:
        db.close()


def _movements(ingredient_id: str, slug: str) -> list[tuple]:
    db = SessionLocal()
    try:
        set_tenant(db, _tenant_id(slug))
        return db.execute(text(
            "SELECT type, quantity FROM stock_movements WHERE ingredient_id = :i ORDER BY created_at"
        ), {"i": ingredient_id}).all()
    finally:
        db.close()


def test_confirm_gherkin_beixa_automatica() -> None:
    h, slug = _setup("baixa")
    queijo = _ingredient(h, "Queijo cheddar", "45.00", "3.00")
    pid = _xburger(h, queijo)
    order = client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 2}]}).json()

    resp = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "confirmed"

    assert _stock(queijo, slug) == "2.94"  # 3.00 − 2 × 0.030
    mov = _movements(queijo, slug)
    assert len(mov) == 1
    assert mov[0][0] == "sale"


def test_confirm_is_idempotent() -> None:
    h, slug = _setup("idemp")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    again = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert again.status_code == 200
    assert _stock(queijo, slug) == "0.97"          # baixa aplicada UMA vez
    assert len(_movements(queijo, slug)) == 1


def test_insufficient_becomes_confirmed_pending_stock() -> None:
    h, slug = _setup("pend")
    queijo = _ingredient(h, "Queijo", "45.00", "0.020")   # X-Burger exige 0.030
    pid = _xburger(h, queijo)
    order = client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    resp = client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "confirmed_pending_stock"
    assert _stock(queijo, slug) == "0.02"          # nada foi baixado
    assert len(_movements(queijo, slug)) == 0


def test_outbox_reprocessed_is_noop() -> None:
    h, slug = _setup("reproc")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    assert _stock(queijo, slug) == "0.97"

    tenant_id = _tenant_id(slug)
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)  # outbox_events tem RLS — sessão precisa do tenant ativo
        row = db.execute(text("SELECT id FROM outbox_events WHERE payload->>'order_id' = :oid"), {"oid": order["id"]}).one()
        db.execute(text("UPDATE outbox_events SET status = 'pending' WHERE id = :id"), {"id": row[0]})
        db.commit()
    finally:
        db.close()

    from uuid import UUID

    from app.modules.orders.outbox import drain_outbox

    drain_outbox(UUID(tenant_id))

    assert _stock(queijo, slug) == "0.97"          # reprocessar não baixa de novo
    assert len(_movements(queijo, slug)) == 1


def test_events_expose_outbox_status() -> None:
    h, _ = _setup("eventos")
    queijo = _ingredient(h, "Queijo", "45.00", "1.00")
    pid = _xburger(h, queijo)
    order = client.post("/api/v1/pedidos", headers=h, json={"items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/v1/pedidos/{order['id']}/confirmar", headers=h)
    resp = client.get(f"/api/v1/pedidos/{order['id']}/eventos", headers=h)
    assert resp.status_code == 200
    assert any(e["outbox_status"] == "processed" for e in resp.json()["events"])
```

- [ ] **Step 2: Criar `orders/outbox.py`**

```python
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.db import SessionLocal, set_tenant
from app.modules.catalog.models import StockLevel, StockMovement
from app.modules.orders.models import Order, OrderEvent, OrderItem, OutboxEvent


def drain_outbox(tenant_id: UUID) -> None:
    db = SessionLocal()
    try:
        set_tenant(db, tenant_id)
        while True:
            event = db.scalar(
                select(OutboxEvent)
                .where(OutboxEvent.tenant_id == tenant_id, OutboxEvent.status == "pending")
                .order_by(OutboxEvent.created_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            if event is None:
                break
            _process(db, tenant_id, event)
            db.commit()
    finally:
        db.close()


def _process(db: Session, tenant_id: UUID, event: OutboxEvent) -> None:
    if event.event_type != "order.confirmed":
        event.status = "failed"
        event.last_error = "unsupported event type"
        return

    order = db.get(Order, UUID(event.payload["order_id"]))
    if order is None:
        event.status = "failed"
        event.last_error = "order not found"
        return

    required: defaultdict[UUID, Decimal] = defaultdict(Decimal)
    items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
    for item in items:
        for snap in item.recipe_snapshot:
            required[UUID(snap["ingredient_id"])] += item.quantity * Decimal(snap["quantity"])

    # movimentos já existentes para o pedido (idempotência: reprocessar é no-op)
    done = set(
        db.scalars(
            select(StockMovement.ingredient_id).where(
                StockMovement.reference_type == "order", StockMovement.reference_id == order.id
            )
        ).all()
    )
    remaining = {i: n for i, n in required.items() if n > 0 and i not in done}
    if not remaining:
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        return

    rows: dict[UUID, StockLevel] = {}
    for ingredient_id in remaining:
        sl = db.scalar(
            select(StockLevel)
            .where(StockLevel.store_id == order.store_id, StockLevel.ingredient_id == ingredient_id)
            .with_for_update()
        )
        rows[ingredient_id] = sl

    if any(sl is None or sl.quantity < remaining[i] for i, sl in rows.items()):
        order.status = "confirmed_pending_stock"
        db.add(OrderEvent(
            tenant_id=tenant_id, order_id=order.id, event_type="inventory.shortage",
            from_status="confirmed", to_status="confirmed_pending_stock",
            payload={"detail": "Estoque insuficiente no momento da baixa."},
        ))
        event.status = "failed"
        event.last_error = "insufficient stock"
        return

    for ingredient_id, need in remaining.items():
        sl = rows[ingredient_id]
        db.execute(
            update(StockLevel)
            .where(StockLevel.id == sl.id, StockLevel.quantity >= need)
            .values(quantity=StockLevel.quantity - need)
        )
        db.add(StockMovement(
            tenant_id=tenant_id, store_id=order.store_id, ingredient_id=ingredient_id,
            type="sale", quantity=-need, unit_cost=sl.average_cost,
            reference_type="order", reference_id=order.id,
            idempotency_key=f"order.confirmed:{order.id}:{ingredient_id}",
        ))

    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
```

> Se dois workers processassem o mesmo evento, o `idempotency_key` unique + o check de `done` garantem uma única baixa; o `UniqueViolation` seria tratado como processamento prévio (aceito nesta fatia, Fase 2 com RabbitMQ usa dedupe no broker).

- [ ] **Step 3: Modificar `orders/service.py` (helper `availability_ok`) e `orders/routes.py` (confirmar/eventos)**

`service.py` — ajustes:

```python
def availability_ok(db: Session, tid: UUID, store_id: UUID, items: list[tuple[UUID, int]]) -> bool:
    try:
        availability(db, tid, store_id, items)
        return True
    except DomainError as exc:
        if exc.code == "insufficient_stock":
            return False
        raise
```

`routes.py` — adicionar (importar `BackgroundTasks`, `OutboxEvent`, `drain_outbox`):

```python
@router.post("/pedidos/{order_id}/confirmar")
def confirm_order(order_id: UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_tenant_db)) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if order.status in ("confirmed", "confirmed_pending_stock"):
        return _to_out(db, order)  # idempotente
    if order.status != "received":
        raise DomainError("invalid_state", "Pedido não pode ser confirmado nesse estado.", status.HTTP_409_CONFLICT)

    from app.modules.orders.service import availability_ok
    ok = availability_ok(db, tid, order.store_id, [(i.product_id, i.quantity) for i in _items_of(db, order.id)])
    order.status = "confirmed" if ok else "confirmed_pending_stock"
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="status.changed",
                      from_status="received", to_status=order.status))
    db.add(OutboxEvent(tenant_id=tid, event_type="order.confirmed",
                       payload={"order_id": str(order.id)}, idempotency_key=f"order.confirmed:{order.id}"))
    db.commit()
    background_tasks.add_task(drain_outbox, tid)
    return _to_out(db, order)


@router.get("/pedidos/{order_id}/eventos")
def order_events(order_id: UUID, db: Session = Depends(get_tenant_db)) -> dict:
    order = db.get(Order, order_id)
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    events = db.scalars(select(OrderEvent).where(OrderEvent.order_id == order_id).order_by(OrderEvent.created_at)).all()
    outbox = db.scalars(
        select(OutboxEvent).where(OutboxEvent.payload["order_id"].astext == str(order_id))
    ).all()
    outbox_status = {o.event_type: o.status for o in outbox}
    return {
        "order_id": str(order_id),
        "status": order.status,
        "events": [
            {
                "event_type": e.event_type, "from_status": e.from_status, "to_status": e.to_status,
                "created_at": e.created_at.isoformat(), "outbox_status": outbox_status.get(e.event_type),
            }
            for e in events
        ],
    }
```

> `_items_of(db, order_id)` = `db.scalars(select(OrderItem).where(OrderItem.order_id == order_id)).all()` (helper local).

- [ ] **Step 4: Rodar suite completa de integração**

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/integration
```

Expected: todos verdes, incluindo o Gherkin de baixa automática e idempotência.

- [ ] **Step 5: Commit**

```bash
git add backend/app && git commit -m "feat(orders): confirmação com outbox + baixa idempotente (gherkin)"
```

---

### Task 9: Endpoint de margem

**Files:**
- Modify: `backend/app/modules/catalog/costing.py` (função `margin`), `backend/app/modules/catalog/routes.py` (`GET /produtos/{id}/margem`)
- Create: `backend/app/tests/unit/test_margem.py`

**Interfaces:**
- Postcondition: `GET /api/v1/produtos/{id}/margem` → `{"product_id", "name", "price", "cost", "margin_value", "margin_percent"}`. Custo = `Σ (ficha.quantity × insumo.average_cost)` da ficha **ativa**, arredondado a 2 casas (gherkin X-Burger); `margin_percent` = `(price − cost)/price × 100` arredondado 2 casas, `None` se `price = 0`.

- [ ] **Step 1: Testes primeiro (TDD)**

`backend/app/tests/unit/test_margem.py`:

```python
from decimal import Decimal

from app.modules.catalog.costing import margin


def test_price_minus_cost() -> None:
    value, percent = margin(Decimal("20.00"), Decimal("3.35"))
    assert value == Decimal("16.65")
    assert percent == Decimal("83.25")


def test_percent_none_when_price_zero() -> None:
    value, percent = margin(Decimal("0"), Decimal("3.35"))
    assert value == Decimal("-3.35")
    assert percent is None
```

- [ ] **Step 2: `costing.py` — função `margin`**

```python
def margin(price: Decimal, cost: Decimal) -> tuple[Decimal, Decimal | None]:
    value = (price - cost).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    percent = None
    if price > 0:
        percent = ((price - cost) / price * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return value, percent
```

- [ ] **Step 3: Rota `GET /produtos/{id}/margem` (append em `catalog/routes.py`)**

```python
@router.get("/produtos/{product_id}/margem")
def get_margin(product_id: UUID, db: Session = Depends(get_tenant_db)) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    recipe = db.scalar(select(Recipe).where(Recipe.product_id == product_id, Recipe.status == "active").order_by(Recipe.version.desc()).limit(1))
    cost = Decimal("0.00")
    if recipe is not None:
        items = db.scalars(select(RecipeItem).where(RecipeItem.recipe_id == recipe.id)).all()
        cost = recipe_cost([(it.quantity, db.get(Ingredient, it.ingredient_id).average_cost) for it in items])
    value, percent = margin(product.price, cost)
    return {
        "product_id": str(product_id),
        "name": product.name,
        "price": str(product.price),
        "cost": str(cost),
        "margin_value": str(value),
        "margin_percent": None if percent is None else str(percent),
    }
```

- [ ] **Step 4: Rodar**

```bash
cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .
../.venv/bin/pytest -q app/tests/unit/test_margem.py
```

- [ ] **Step 5: Commit**

```bash
git add backend/app && git commit -m "feat(catalog): endpoint de margem (custo da ficha vs preço)"
```

---

### Task 10: Seed de demonstração

**Files:**
- Create: `backend/scripts/seed.py`

**Interfaces:**
- Preconditions: migrations aplicadas; `make up`.
- Postconditions: `make seed` (idempotente — se tenant `demo` existir, sai com aviso) cria tenant `demo`, loja + unidades base, 3 insumos, produto X-Burger com ficha, um pedido **confirmado** (baixa aplicada). Fluxo percorrível em 1 minuto via API/frontend.

**Dados:**
- Insumos: `Queijo cheddar` (kg, 45.00, saldo 3.000), `Pão brioche` (un, 2.00, saldo 50), `Carne 160g` (kg, 30.00, saldo 5.000).
- Produto: `X-Burger`, preço 20.00; ficha: queijo 0.030 kg, pão 2 un, carne 0.150 kg → custo 1.35 + 4.00 + 4.50 = **9.85**; margem 10.15 / 50.75%.
- Pedido: 1 X-Burger, status `confirmed`; acesso `dono@demo.local` / senha `demo1234`.

- [ ] **Step 1: Criar `backend/scripts/seed.py`**

```python
"""Seed de demonstração do StockChef.

Uso: cd backend && ../.venv/bin/python scripts/seed.py
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.db import SessionLocal, set_tenant
from app.modules.catalog.models import Ingredient, Product, Recipe, RecipeItem, StockLevel, Store, Unit
from app.modules.catalog.service import default_store
from app.modules.identity.models import Tenant, User
from app.modules.identity.security import hash_password
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.routes import confirm_order
from app.modules.orders.outbox import drain_outbox

EMAIL = "dono@demo.local"
PASSWORD = "demo1234"
SLUG = "demo"


def seed() -> None:
    db = SessionLocal()
    try:
        if db.scalar(select(Tenant).where(Tenant.slug == SLUG)):
            print("Tenant 'demo' já existe — nada a fazer.")
            return

        tenant = Tenant(name="Lanches Demo", slug=SLUG, status="active")
        db.add(tenant)
        db.flush()
        set_tenant(db, tenant.id)

        db.add(Store(tenant_id=tenant.id, name="Loja principal", status="active"))
        for symbol, name, typ in (
            ("kg", "Quilograma", "mass"), ("g", "Grama", "mass"),
            ("ml", "Mililitro", "volume"), ("l", "Litro", "volume"), ("un", "Unidade", "count"),
        ):
            db.add(Unit(tenant_id=tenant.id, name=name, symbol=symbol, type=typ))
        db.flush()

        user = User(tenant_id=tenant.id, email=EMAIL, password_hash=hash_password(PASSWORD),
                    name="Dona Demo", role="owner", status="active")
        db.add(user)
        db.flush()

        store = default_store(db, tenant.id)
        kg = db.scalar(select(Unit).where(Unit.tenant_id == tenant.id, Unit.symbol == "kg"))
        un = db.scalar(select(Unit).where(Unit.tenant_id == tenant.id, Unit.symbol == "un"))

        specs = [
            ("Queijo cheddar", kg.id, Decimal("45.00"), Decimal("3.000")),
            ("Pão brioche", un.id, Decimal("2.00"), Decimal("50")),
            ("Carne 160g", kg.id, Decimal("30.00"), Decimal("5.000")),
        ]
        ingredients: dict[str, Ingredient] = {}
        for name, unit_id, cost, stock_qty in specs:
            ing = Ingredient(tenant_id=tenant.id, name=name, base_unit_id=unit_id, average_cost=cost, status="active")
            db.add(ing)
            db.flush()
            db.add(StockLevel(tenant_id=tenant.id, store_id=store.id, ingredient_id=ing.id,
                              quantity=stock_qty, average_cost=cost))
            ingredients[name] = ing

        FICHA = (("Queijo cheddar", "0.030"), ("Pão brioche", "2"), ("Carne 160g", "0.150"))

        product = Product(tenant_id=tenant.id, store_id=store.id, name="X-Burger",
                          price=Decimal("20.00"), preparation_time_minutes=15)
        db.add(product)
        db.flush()
        recipe = Recipe(tenant_id=tenant.id, product_id=product.id, version=1, status="active")
        db.add(recipe)
        for name, qty in FICHA:
            db.add(RecipeItem(tenant_id=tenant.id, recipe_id=recipe.id,
                              ingredient_id=ingredients[name].id, quantity=Decimal(qty), unit_id=ingredients[name].base_unit_id))
        db.flush()

        order = Order(tenant_id=tenant.id, store_id=store.id, code="SC-DEMO-1", status="received",
                      subtotal=Decimal("20.00"), total=Decimal("20.00"))
        db.add(order)
        db.flush()
        recipe_snapshot = [{"ingredient_id": str(ingredients[n].id), "quantity": q, "unit_id": str(ingredients[n].base_unit_id)} for n, q in FICHA]
        db.add(OrderItem(tenant_id=tenant.id, order_id=order.id, product_id=product.id, quantity=1,
                         unit_price=Decimal("20.00"), total_price=Decimal("20.00"),
                         recipe_snapshot=recipe_snapshot))
        db.commit()

        confirm_order(order_id=order.id, background_tasks=BackgroundTasks(), db=db)
        drain_outbox(tenant.id)
        db.commit()

        print("Seed concluído:")
        print(f"  login: {EMAIL} / {PASSWORD}")
        print(f"  tenant: {SLUG} · X-Burger custo 9.85 · margem 50.75%")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
```

> `OrderEvent`/`OutboxEvent` são criados por `confirm_order`; o `BackgroundTasks()` no script é inerte (task roda via `drain_outbox(tenant.id)` explícita logo abaixo — sem servidor HTTP). O snapshot acima usa os mesmos IDs/quantidades da ficha ativa (mesmo formato do endpoint de criação).

- [ ] **Step 2: Executar e validar o fluxo em 1 minuto**

```bash
make seed
cd backend && ../.venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.post("/api/v1/auth/login", json={"tenant_slug": "demo", "email": "dono@demo.local", "password": "demo1234"})
assert r.status_code == 200
h = {"Authorization": f"Bearer {r.json()['access_token']}"}
pedidos = c.get("/api/v1/pedidos", headers=h).json()
assert len(pedidos) == 1 and pedidos[0]["status"] == "confirmed"
insumos = c.get("/api/v1/insumos", headers=h).json()
queijo = next(i for i in insumos if i["name"] == "Queijo cheddar")
assert queijo["stock_total"] == "2.97"   # 3.000 − 0.030
print("Seed OK")
PY
```

Expected: `Seed OK`; estoque do queijo em 2.97 após a baixa do pedido demo.

- [ ] **Step 3: Commit**

```bash
git add backend/scripts && git commit -m "feat(seed): tenant demo com ficha X-Burger + pedido confirmado"
```

---

### Task 11: Frontend — scaffold + tela de login + cliente API

**Files:**
- Create: `frontend/` (Vite + React + TS), `frontend/biome.json`, `frontend/src/api/client.ts`, `frontend/src/auth/AuthContext.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/App.tsx`, `frontend/src/test/setup.ts`, `frontend/src/test/login.test.tsx`

**Interfaces:**
- Preconditions: backend no ar (`make dev-backend`); Vite proxy `/api → :8000`.
- Postconditions: `npm run dev` com `npm run test` e `npm run lint` (Biome) e `npm run build` verdes. Login funcional com refresh automático (`/auth/refresh` cookie httpOnly).

- [ ] **Step 1: Gerar o scaffold do Vite (react + ts)**

```bash
mkdir -p frontend
cd frontend && npm create vite@latest . -- --template react-ts
```

> Se o `create-vite` fizer pergunta interativa ("install and start now?", etc.), responder/off com `--no-interactive` quando suportado ou confirmar a opção padrão; o resultado esperado é `package.json`, `tsconfig.*`, `vite.config.ts`, `src/main.tsx` presentes e `npm run build` funcionando.

- [ ] **Step 2: Dependências e scripts**

```bash
cd frontend
npm install
npm install react-router-dom @tanstack/react-query
npm install -D biome vitest jsdom @testing-library/react @testing-library/user-event @testing-library/jest-dom
```

`frontend/package.json` — scripts:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "typecheck": "tsc -b --noEmit",
    "lint": "biome check ."
  }
}
```

- [ ] **Step 3: `biome.json`, `vite.config.ts` (proxy + vitest) e `tsconfig`**

`frontend/biome.json`:

```json
{
  "$schema": "https://biomejs.dev/schemas/2.9.2/schema.json",
  "vcs": { "enabled": true, "clientKind": "git", "useIgnoreFile": true },
  "files": { "includes": ["src/**"] },
  "formatter": { "enabled": true, "indentStyle": "space", "indentWidth": 2, "lineWidth": 100 },
  "linter": { "enabled": true, "rules": { "recommended": true } }
}
```

`frontend/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
  },
});
```

`frontend/src/test/setup.ts`:

```ts
import "@testing-library/jest-dom/vitest";
```

- [ ] **Step 4: Cliente API com refresh automático**

`frontend/src/api/client.ts`:

```ts
const TOKEN_KEY = "sc_token";

export class ApiError extends Error {
  code?: string;
  constructor(message: string, public status: number, code?: string) {
    super(message);
    this.code = code;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function refreshSession(): Promise<boolean> {
  const res = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
  if (!res.ok) return false;
  const body = await res.json();
  setToken(body.access_token);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");

  let res = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "include" });

  if (res.status === 401) {
    const ok = await refreshSession();
    if (ok) {
      const retryHeaders = new Headers(headers);
      const fresh = getToken();
      if (fresh) retryHeaders.set("Authorization", `Bearer ${fresh}`);
      res = await fetch(`/api/v1${path}`, { ...init, headers: retryHeaders, credentials: "include" });
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Erro inesperado.", res.status, body.code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const login = (body: { tenant_slug: string; email: string; password: string }) =>
  api<{ access_token: string; user: { id: string; email: string; name: string; role: string } }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify(body) },
  );
```

- [ ] **Step 5: `AuthContext.tsx`**

```tsx
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { ApiError, api, clearToken, getToken } from "../api/client";

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextValue {
  user: SessionUser | null;
  login: (tenantSlug: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);

  const login = useCallback(async (tenantSlug: string, email: string, password: string) => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_slug: tenantSlug, email, password }),
    });
    if (!res.ok) throw new ApiError("Credenciais inválidas.", res.status);
    const body = await res.json();
    localStorage.setItem("sc_token", body.access_token);
    setUser(body.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
      setUser(null);
    }
  }, []);

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
```

> Na implementação, restaurar usuário ao carregar a página: se `getToken()` existir, chamar `/auth/me` no mount do provider (mesmo erro 401 já dispara refresh). Sinalizar acessibilidade dos labels na review.

- [ ] **Step 6: `LoginPage.tsx`** (pt-BR, botão verbal)

```tsx
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [tenant, setTenant] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(tenant, email, password);
      navigate("/");
    } catch {
      setError("Credenciais inválidas.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-dvh max-w-md place-items-center p-8">
      <form onSubmit={onSubmit} className="w-full space-y-4">
        <h1 className="text-2xl font-semibold">Acessar StockChef</h1>
        <label className="block space-y-1">
          <span className="text-sm">Tenant</span>
          <input value={tenant} onChange={(e) => setTenant(e.target.value)} required className="w-full rounded border px-3 py-2" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">E-mail</span>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required className="w-full rounded border px-3 py-2" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Senha</span>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required className="w-full rounded border px-3 py-2" />
        </label>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        <button type="submit" disabled={loading} className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
          {loading ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </main>
  );
}
```

> `aria-label`s nos inputs para o teste (`getByLabelText(/tenant/i)`, etc.) — o `<span>` é o label programático; validar acessibilidade na review.

- [ ] **Step 7: `App.tsx` com rotas + `main.tsx` e página dashboard placeholder**

```tsx
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import LoginPage from "./pages/LoginPage";

function Protected({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Protected><DashboardPage /></Protected>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
```

`main.tsx`: trocar conteúdo gerado por `createRoot(document.getElementById("root")!).render(<React.StrictMode><App /></React.StrictMode>)` + import `./index.css`.

`src/pages/DashboardPage.tsx`:

```tsx
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <button onClick={() => void logout()} className="text-sm text-red-600">Sair</button>
        </div>
      </header>
      <nav className="flex gap-3">
        <Link to="/insumos" className="rounded border px-4 py-2">Insumos</Link>
        <Link to="/produtos" className="rounded border px-4 py-2">Produtos</Link>
        <Link to="/pedidos" className="rounded border px-4 py-2">Pedidos</Link>
      </nav>
      <p className="text-gray-600 mb-64">Vertical slice: insumo → produto → pedido → baixa → margem.</p>
    </main>
  );
}
```

> Home temporária: links de navegação apontam para rotas criadas na Task 12.

- [ ] **Step 8: Teste de login (Vitest + Testing Library)**

`frontend/src/test/login.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import LoginPage from "../pages/LoginPage";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } });
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("faz login e guarda o token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        if (String(url) === "/api/v1/auth/login") {
          return jsonResponse({ access_token: "abc", user: { id: "1", email: "a@b.com", name: "A", role: "owner" } });
        }
        throw new Error(`fetch inesperado: ${url}`);
      }),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText(/tenant/i), "demo");
    await userEvent.type(screen.getByLabelText(/e-mail/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/senha/i), "demo1234");
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => expect(localStorage.getItem("sc_token")).toBe("abc"));
  });
});
```

- [ ] **Step 9: Shadcn/ui base (botões/table/card/dialog para as telas)**

```bash
cd frontend
npx shadcn@latest init 
```

> Ainda não geramos tokens de design próprios; o init do shadcn cria `components.json`, `lib/utils.ts` e o CSS base com Tailwind v4. Escolher base color `neutral` e "global CSS vars". Depois:

```bash
npx shadcn@latest add button input label card table badge dialog select
```

> Se o CLI pedir confirmação interativa, confirmar defaults. O objetivo aqui é apenas os componentes base; `components.json` fica versionado.

- [ ] **Step 10: Rodar tudo**

```bash
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```

Expected: tudo verde (TDD: o teste falha antes da implementação de `login`).

- [ ] **Step 11: Commit**

```bash
git add frontend && git commit -m "feat(frontend): scaffold vite + login com refresh automático e testes"
```

---

### Task 12: Frontend — páginas de insumos, produtos (ficha) e pedidos (confirmar)

**Files:**
- Create: `frontend/src/pages/InsumosPage.tsx`, `frontend/src/pages/ProdutosPage.tsx`, `frontend/src/pages/PedidosPage.tsx`, `frontend/src/pages/PedidoDetalhePage.tsx`, `frontend/src/api/types.ts`, `frontend/src/test/pedido.test.tsx`
- Modify: `frontend/src/App.tsx` (rotas)

**Interfaces:**
- Postconditions: navegação `/insumos`, `/produtos`, `/pedidos`, `/pedidos/:id` autenticada (Protected). CRUD simples + `Confirmar` pedido chama `POST /pedidos/{id}/confirmar` e mostra `stock movements`/status. Teste do fluxo "confirmar pedido" (Vitest).
- pt-BR; números com `Number()` (decires vêm como string da API); barra lateral/nav simples.

- [ ] **Step 1: Tipos da API**

`frontend/src/api/types.ts`:

```ts
export interface Insumo {
  id: string;
  name: string;
  category?: string | null;
  base_unit: { id: string; symbol: string };
  average_cost: string;
  minimum_stock: string;
  stock_total: string;
}

export interface Producto {
  id: string;
  name: string;
  description?: string | null;
  price: string;
  active: boolean;
  preparation_time_minutes: number;
}

export interface RecipeItemOut {
  ingredient_id: string;
  name: string;
  unit_symbol: string;
  quantity: string;
  cost: string;
}

export interface RecipeOut {
  product_id: string;
  status: string;
  version: number;
  items: RecipeItemOut[];
  total_cost: string;
}

export interface Margem {
  product_id: string;
  name: string;
  price: string;
  cost: string;
  margin_value: string;
  margin_percent: string | null;
}

export interface PedidoItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  total_price: string;
}

export interface Pedido {
  id: string;
  code: string;
  status: string;
  customer_name?: string | null;
  customer_phone?: string | null;
  subtotal: string;
  total: string;
  notes?: string | null;
  created_at: string;
  order_items: PedidoItem[];
}

export interface Evento {
  event_type: string;
  from_status?: string | null;
  to_status?: string | null;
  created_at: string;
  outbox_status?: string | null;
}

export const STATUS_LABEL: Record<string, string> = {
  received: "Recebido",
  confirmed: "Confirmado",
  confirmed_pending_stock: "Confirmado c/ pendência",
  preparing: "Em preparo",
  ready: "Pronto",
  out_for_delivery: "Em entrega",
  delivered: "Entregue",
  completed: "Concluído",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
};
```

- [ ] **Step 2: `InsumosPage.tsx`** (lista + criar + editar custo, TanStack Query)

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { api } from "../api/client";
import type { Insumo } from "../api/types";

export default function InsumosPage() {
  const qc = useQueryClient();
  const { data: insumos = [] } = useQuery({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("kg");
  const [cost, setCost] = useState("");
  const [stock, setStock] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api<Insumo>("/insumos", {
        method: "POST",
        body: JSON.stringify({
          name,
          base_unit_symbol: symbol,
          average_cost: cost,
          initial_stock: stock || "0",
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insumos"] });
      setName(""); setCost(""); setStock("");
    },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Insumos</h1>

      <form
        onSubmit={(e: FormEvent) => { e.preventDefault(); create.mutate(); }}
        className="flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <label className="space-y-1">
          <span className="text-sm">Nome</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required className="rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Unidade</span>
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)} className="rounded border px-3 py-2">
            {["kg", "g", "un", "ml", "l"].map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-sm">Custo (R$/un)</span>
          <input value={cost} onChange={(e) => setCost(e.target.value)} required className="rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Saldo inicial</span>
          <input value={stock} onChange={(e) => setStock(e.target.value)} className="rounded border px-3 py-2" />
        </label>
        <button type="submit" disabled={create.isPending} className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50">
          Criar insumo
        </button>
      </form>

      <table className="w-full text-sm">
        <thead><tr className="text-left"><th>Nome</th><th>Un.</th><th>Custo</th><th>Estoque</th></tr></thead>
        <tbody>
          {insumos.map((i) => (
            <tr key={i.id} className="border-t">
              <td className="py-2">{i.name}</td>
              <td>{i.base_unit.symbol}</td>
              <td>R$ {Number(i.average_cost).toFixed(2)}</td>
              <td>{Number(i.stock_total).toFixed(i.base_unit.symbol === "un" ? 0 : 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

- [ ] **Step 3: `ProdutosPage.tsx`** (lista + criar + editor de ficha + margem)

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { Margem, Producto, RecipeOut } from "../api/types";

export default function ProdutosPage() {
  const qc = useQueryClient();
  const { data: produtos = [] } = useQuery({ queryKey: ["produtos"], queryFn: () => api<Producto[]>("/produtos") });
  const { data: insumos = [] } = useQuery<any[]>({ queryKey: ["insumos"], queryFn: () => api("/insumos") });

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () => api<Producto>("/produtos", { method: "POST", body: JSON.stringify({ name, price }) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["produtos"] }); setName(""); setPrice(""); },
  });

  const { data: ficha } = useQuery({
    queryKey: ["ficha", selected],
    queryFn: () => api<RecipeOut>(`/produtos/${selected}/ficha-tecnica`),
    enabled: !!selected,
  });
  const { data: margem } = useQuery({
    queryKey: ["margem", selected],
    queryFn: () => api<Margem>(`/produtos/${selected}/margem`),
    enabled: !!selected,
  });

  const [linhas, setLinhas] = useState<{ ingredient_id: string; quantity: string }[]>([{ ingredient_id: "", quantity: "" }]);

  const saveFicha = useMutation({
    mutationFn: () => api<RecipeOut>(`/produtos/${selected}/ficha-tecnica`, {
      method: "POST",
      body: JSON.stringify({ items: linhas }),
    }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["ficha", selected] }); qc.invalidateQueries({ queryKey: ["margem", selected] }); },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Produtos</h1>
      <form onSubmit={(e) => { e.preventDefault(); create.mutate(); }} className="flex flex-wrap items-end gap-3 rounded border p-4">
        <label className="space-y-1"><span className="text-sm">Nome</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required className="rounded border px-3 py-2" />
        </label>
        <label className="space-y-1"><span className="text-sm">Preço (R$)</span>
          <input value={price} onChange={(e) => setPrice(e.target.value)} required className="rounded border px-3 py-2" />
        </label>
        <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white">Criar produto</button>
      </form>

      <div className="grid gap-6 md:grid-cols-2">
        <ul className="space-y-2">
          {produtos.map((p) => (
            <li key={p.id}>
              <button onClick={() => setSelected(p.id)} className={`w-full rounded border p-3 text-left ${selected === p.id ? "border-blue-500" : ""}`}>
                <div className="font-medium">{p.name}</div>
                <div className="text-sm text-gray-600">R$ {Number(p.price).toFixed(2)}</div>
              </button>
            </li>
          ))}
        </ul>

        <section className="space-y-4 rounded border p-4">
          <h2 className="font-semibold">Ficha técnica</h2>
          {linhas.map((linha, idx) => (
            <div key={idx} className="flex gap-2">
              <select
                value={linha.ingredient_id}
                onChange={(e) => setLinhas((ls) => ls.map((l, i) => (i === idx ? { ...l, ingredient_id: e.target.value } : l)))}
                className="flex-1 rounded border px-3 py-2"
              >
                <option value="">Insumo…</option>
                {insumos.map((i) => <option key={i.id} value={i.id}>{i.name} ({i.base_unit.symbol})</option>)}
              </select>
              <input
                value={linha.quantity}
                placeholder="qtd"
                onChange={(e) => setLinhas((ls) => ls.map((l, i) => (i === idx ? { ...l, quantity: e.target.value } : l)))}
                className="w-24 rounded border px-3 py-2"
              />
            </div>
          ))}
          <div className="flex gap-2">
            <button onClick={() => setLinhas((ls) => [...ls, { ingredient_id: "", quantity: "" }])} className="rounded border px-3 py-2 text-sm">+ insumo</button>
            <button onClick={() => selected && saveFicha.mutate()} disabled={!selected} className="rounded bg-blue-600 px-4 py-2 text-white text-sm disabled:opacity-50">
              Salvar ficha
            </button>
          </div>
          {ficha && (
            <ul className="text-sm">
              {ficha.items.map((it) => (
                <li key={it.ingredient_id} className="flex justify-between">
                  <span>{it.name} · {it.quantity} {it.unit_symbol}</span>
                  <span>R$ {Number(it.cost).toFixed(2)}</span>
                </li>
              ))}
              <li className="mt-2 flex justify-between font-medium">
                <span>Custo</span><span>R$ {Number(ficha.total_cost).toFixed(2)}</span>
              </li>
            </ul>
          )}
          {margem && margem.margin_percent !== null && (
            <p className="text-sm">Margem: <strong>{margem.margin_percent}%</strong> · R$ {margem.margin_value}</p>
          )}
        </section>
      </div>
    </main>
  );
}
```

- [ ] **Step 4: `PedidosPage.tsx` (lista + detalhe + confirmar) e `PedidoDetalhePage.tsx`**

`PedidosPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { STATUS_LABEL, type Pedido } from "../api/types";

export default function PedidosPage() {
  const { data: pedidos = [] } = useQuery({ queryKey: ["pedidos"], queryFn: () => api<Pedido[]>("/pedidos") });
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Pedidos</h1>
      <table className="w-full text-sm">
        <thead><tr className="text-left"><th>Código</th><th>Cliente</th><th>Itens</th><th>Total</th><th>Status</th></tr></thead>
        <tbody>
          {pedidos.map((p) => (
            <tr key={p.id} className="border-t">
              <td className="py-2"><Link to={`/pedidos/${p.id}`} className="text-blue-600">{p.code}</Link></td>
              <td>{p.customer_name ?? "—"}</td>
              <td>{p.order_items.reduce((acc, it) => acc + it.quantity, 0)}</td>
              <td>R$ {Number(p.total).toFixed(2)}</td>
              <td>{STATUS_LABEL[p.status] ?? p.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
```

`PedidoDetalhePage.tsx` (com `Confirmação` de pedido → testada na Step 5):

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { STATUS_LABEL, type Evento, type Pedido } from "../api/types";

function usePedido(id: string) {
  return useQuery({ queryKey: ["pedido", id], queryFn: () => api<Pedido>(`/pedidos/${id}`) });
}

export default function PedidoDetalhePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data: pedido } = usePedido(id);
  const { data: eventos } = useQuery({
    queryKey: ["pedido-eventos", id],
    queryFn: () => api<{ order_id: string; status: string; events: Evento[] }>(`/pedidos/${id}/eventos`),
    enabled: !!id,
  });

  const [aviso, setAviso] = useState("");
  const confirmar = useMutation({
    mutationFn: () => api<Pedido>(`/pedidos/${id}/confirmar`, { method: "POST" }),
    onSuccess: (ped) => {
      qc.invalidateQueries({ queryKey: ["pedido", id] });
      qc.invalidateQueries({ queryKey: ["pedido-eventos", id] });
      if (ped.status === "confirmed_pending_stock") setAviso("Pedido confirmado com pendência de estoque.");
    },
  });

  const podeConfirmar = pedido && ["received"].includes(pedido.status);

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">{pedido?.code ?? "Pedido"}</h1>
      {pedido && <p>Status: <strong>{STATUS_LABEL[pedido.status] ?? pedido.status}</strong></p>}
      {aviso && <p role="alert" className="text-sm text-amber-700">{aviso}</p>}

      <ul className="rounded border p-4">
        {pedido?.order_items.map((it) => (
          <li key={it.product_id} className="flex justify-between py-1">
            <span>{it.quantity}× {it.product_name}</span>
            <span>R$ {Number(it.total_price).toFixed(2)}</span>
          </li>
        ))}
      </ul>
      <p>Total: <strong>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</strong></p>

      {podeConfirmar && (
        <button onClick={() => confirmar.mutate()} disabled={confirmar.isPending} className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50">
          {confirmar.isPending ? "Confirmando…" : "Confirmar pedido"}
        </button>
      )}

      <section>
        <h2 className="font-semibold">Eventos</h2>
        <ul className="text-sm">
          {eventos?.events.map((e, i) => (
            <li key={i} className="flex justify-between py-1">
              <span>{e.event_type}</span>
              <span className="text-gray-500">{e.outbox_status ?? e.created_at}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

> Adicionar `import { useState } from "react";` no topo do arquivo.

- [ ] **Step 5: Teste "confirmar pedido" (Vitest)**

`frontend/src/test/pedido.test.tsx`:

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PedidoDetalhePage from "../pages/PedidoDetalhePage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const pedido = {
  id: "o1", code: "SC-ABC1", status: "received",
  subtotal: "40.00", total: "40.00",
  order_items: [{ product_id: "p1", product_name: "X-Burger", quantity: 2, unit_price: "20.00", total_price: "40.00" }],
};

describe("PedidoDetalhePage", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });

  it("confirma um pedido recebido", async () => {
    vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/pedidos/o1") return jsonResponse(pedido);
      if (u === "/api/v1/pedidos/o1/eventos") return jsonResponse({ order_id: "o1", status: "received", events: [] });
      if (u === "/api/v1/pedidos/o1/confirmar" && init?.method === "POST")
        return jsonResponse({ ...pedido, status: "confirmed" });
      throw new Error(`fetch inesperado: ${u}`);
    }));

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/pedidos/o1"]}>
          <Routes>
            <Route path="/pedidos/:id" element={<PedidoDetalhePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("Recebido");
    await userEvent.click(screen.getByRole("button", { name: /confirmar pedido/i }));
    await waitFor(() => expect(screen.queryByText("Confirmado")).toBeInTheDocument());
  });
});
```

> Assim que `confirmar` muda o status para `confirmed`, a refetch do `pedido` atualiza a tela para "Confirmado". O token ausente não bloqueia porque `api()` só encaminha `Authorization` se houver token.

- [ ] **Step 6: Rotas em `App.tsx` (modificar)**

```tsx
<Route path="/insumos" element={<Protected><InsumosPage /></Protected>} />
<Route path="/produtos" element={<Protected><ProdutosPage /></Protected>} />
<Route path="/pedidos" element={<Protected><PedidosPage /></Protected>} />
<Route path="/pedidos/:id" element={<Protected><PedidoDetalhePage /></Protected>} />
```

Envolver as rotas de negócio com `QueryClientProvider` (no `main.tsx`) para TanStack Query disponível nas páginas.

- [ ] **Step 7: Rodar e ajustar acessibilidade**

```bash
cd frontend && npm run typecheck && npm run lint && npm run test && npm run build
```

Expected: verde. Na review, garantir labels programáticos em todos os inputs (testes de a11y básicos nas telas).

- [ ] **Step 8: Commit**

```bash
git add frontend/src && git commit -m "feat(frontend): páginas admin — insumos, ficha técnica e confirmação de pedido"
```

---

### Task 13: CI completa + README final + revisão da fatia

**Files:**
- Rewrite: `.github/workflows/ci.yml`, `README.md`

**Interfaces:**
- Postconditions: pipeline verde (jobs backend + frontend); `make test`, `make lint` e `make seed` documentados e funcionais; critério de saída do spec §8 atendido: `make test` verde local + CI verde + seed percorrido ponta a ponta via API.

- [ ] **Step 1: Reescrever `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - name: Install
        run: pip install -e "backend[dev]"
      - name: Ruff
        run: cd backend && ruff check .
      - name: Mypy
        run: cd backend && mypy .
      - name: Pytest (testcontainers)
        run: cd backend && pytest -q
        env:
          # testcontainers sobe um Postgres 16 efêmero; DATABASE_URL é definido pelo conftest
          DOCKER_HOST: unix:///var/run/docker.sock

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "24"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install
        run: cd frontend && npm ci
      - name: Biome
        run: cd frontend && npm run lint
      - name: Typecheck
        run: cd frontend && npm run typecheck
      - name: Vitest
        run: cd frontend && npm run test
      - name: Build
        run: cd frontend && npm run build
  compose:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate compose
        run: docker compose config -q
```

> Jobs independentes; o backend usa testcontainers (exige Docker no runner — disponível no GitHub Actions). A migração 0001 roda dentro do `pytest_configure` do conftest.

- [ ] **Step 2: Finalizar `README.md`** (seções: visão, stack, início rápido, make targets, seed, testes/lint, arquitetura, docs)

```markdown
# StockChef

SaaS de delivery próprio + controle de estoque por ficha técnica. Documentação de
produto em `docs/` (PRD, plano, backlog, spec/plan da fatia atual).

## Stack

- **Backend** `backend/`: Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · RLS
- **Frontend** `frontend/`: Node 24 · Vite · React · TypeScript · Tailwind · shadcn/ui · TanStack Query · Biome

## Requisitos

Python 3.12 · Node 24 · Docker + Compose · `make`

## Início rápido

    make install          # .venv + deps backend; npm install frontend
    make up               # PostgreSQL 16 + Redis
    make migrate          # alembic upgrade head (schema completo + RLS)
    make seed             # tenant "demo" com X-Burger e 1 pedido confirmado
    make dev-backend      # API em :8000
    make dev-frontend     # admin em :5173 (proxy /api → :8000)

Login do seed: `dono@demo.local` / `demo1234`.

## Rotas principais (API)

- `/api/v1/auth/register|login|refresh|logout|me`
- `/api/v1/insumos` · `/api/v1/produtos` · `/api/v1/produtos/{id}/ficha-tecnica` · `/api/v1/produtos/{id}/margem`
- `/api/v1/pedidos` · `/api/v1/pedidos/{id}/confirmar` · `/api/v1/pedidos/{id}/eventos`

## Testes e lint

    make test     # pytest (testcontainers) + vitest
    make lint     # ruff + mypy + biome

## Isolamento multi-tenant

RLS no Postgres usando `app.tenant_id` (set_config) em todas as tabelas de negócio;
a role `stockchef_app` não tem BYPASSRLS. Migrações rodam com a role `stockchef`.

## Fora de escopo desta fatia

PWA, pagamentos, entregas, RabbitMQ (outbox in-process já preparado para troca),
agentes IA, billing, conversão de unidades (ficha sempre na unidade-base),
waste_factor. Ver spec §1.
```

- [ ] **Step 3: Rodada final de verificação local**

```bash
make lint && make test       # tudo verde
make seed                    # tenant demo (1x; idempotente)
make dev-backend &           # servidor em background para smoke manual
```

Expected: `ruff`/`mypy`/`biome`/`pytest`/`vitest` verdes.

- [ ] **Step 4: Commit final da fatia**

```bash
git add README.md .github && git commit -m "ci: pipeline completa (backend+frontend) e README final"
```

---

## Critérios de saída da fatia (spec §8)

- [ ] `make test` verde local (backend testcontainers + frontend vitest)
- [ ] CI verde no GitHub Actions (jobs `backend`, `frontend`, `compose`)
- [ ] Fluxo do seed percorrido ponta a ponta via API: login demo → insumos → ficha → pedido → confirmar → baixa → margem/eventos
- [ ] Gherkin de isolamento (403 + RLS) coberto por teste de integração
- [ ] Gherkin de custo X-Burger (1.35) e baixa automática (3.0 → 2.94, idempotente) cobertos

## Revisão final do plano (antes de executar)

1. Consistência de tipos/contratos entre tasks (Models ↔ Routes ↔ Schemas ↔ Frontend `types.ts`).
2. Buscar placeholders `TODO` e anotações de review — resolver antes de rodar (`_DefaultStore`/`_Unit` foram eliminados na revisão; o register usa `Store`/`Unit`).
3. Confirmar decisão de `BackgroundTasks` vs `asyncio.create_task` (documentada na Task 8) com o autor do spec.
4. Conferir que `errors.DomainError` aceita `extra` (definido já na Task 2) e que `tenant_mismatch`/`invalid_credentials` seguem `{detail, code}`.
5. Rodar os planos de teste manualmente para detectar refactors necessários em `_tenant_id`/`_to_out`.
```
