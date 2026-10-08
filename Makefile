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
