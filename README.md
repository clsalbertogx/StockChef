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
