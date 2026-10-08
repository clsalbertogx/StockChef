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
    make up               # PostgreSQL 16
    make migrate          # alembic upgrade head (schema completo + RLS)
    make seed             # tenant "demo" com X-Burger e 1 pedido confirmado
    make dev-backend      # API em :8000
    make dev-frontend     # admin em :5173 (proxy /api → :8000)

Login do seed: `dono@demo.example` / `demo1234`.

## Rotas principais (API)

- `/api/v1/auth/register|login|refresh|logout|me`
- `/api/v1/insumos` · `/api/v1/produtos` · `/api/v1/produtos/{id}/ficha-tecnica` · `/api/v1/produtos/{id}/margem`
- `/api/v1/pedidos` · `/api/v1/pedidos/{id}/confirmar` · `/api/v1/pedidos/{id}/eventos`

## Make targets

    make install          # instala deps (backend + frontend)
    make up               # sobe serviços
    make migrate          # aplica migrações
    make seed             # popula dados demo (idempotente)
    make dev-backend      # roda backend
    make dev-frontend     # roda frontend
    make test             # pytest (testcontainers) + vitest
    make lint             # ruff + mypy + biome

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
