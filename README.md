# StockChef

SaaS de delivery próprio + controle de estoque por ficha técnica. Documentação de produto em `docs/` (PRD, plano, backlog, spec/plan da fatia atual).

## Stack

- **Backend** `backend/`: Python 3.12 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · RLS
- **Frontend** `frontend/`: Node 20+ · Vite · React 18 · TypeScript · Tailwind CSS · shadcn/ui · TanStack Query · Biome

## Requisitos

Python 3.12 · Node 20+ · Docker + Compose · `make`

## Início rápido

```bash
make install          # .venv + deps backend; npm install frontend
make up               # PostgreSQL 16 + Redis
make migrate          # alembic upgrade head (schema completo + RLS)
make seed             # tenant "demo" com X-Burger e 1 pedido confirmado
make dev-backend      # API em :8000
make dev-frontend     # admin em :5173 (proxy /api → :8000)
```

Login do seed: `dono@demo.example` / `demo1234`.

### Com Docker Compose (produção-like)

```bash
docker compose up -d --build
# API: http://localhost:8000
# Frontend: http://localhost:5173
```

## Rotas principais (API)

### Autenticação
- `POST /api/v1/auth/register` — cria tenant + loja + owner + unidades + auto-login
- `POST /api/v1/auth/login` — login com fluxo email-first (descobre tenants do email)
- `GET /api/v1/auth/tenants-by-email?email=` — descoberta de tenants (público)
- `POST /api/v1/auth/refresh` · `POST /api/v1/auth/logout` · `GET /api/v1/auth/me`

### Catálogo & Estoque
- `POST/GET/PATCH /api/v1/insumos` — CRUD + estoque inicial
- `POST/GET /api/v1/produtos` — CRUD + ficha técnica + margem
- `POST/GET/PATCH /api/v1/produtos/{id}/ficha-tecnica` — receita (itens + custo)
- `GET /api/v1/produtos/{id}/margem` — preço, custo, margem %/valor
- `POST/GET/PATCH /api/v1/produtos/{id}/adicionais` — modificadores (grupos, min/max)
- `POST/GET /api/v1/perdas` · `GET /api/v1/movimentos` · `GET /api/v1/estoque/critico`

### Compras
- `POST/GET /api/v1/fornecedores` — CRUD
- `GET /api/v1/compras/sugestao` — sugestão por regra (mínimo + lead + consumo + segurança)
- `POST/GET /api/v1/compras` · `PATCH /api/v1/compras/{id}/aprovar|cancelar`
- `POST /api/v1/compras/{id}/recebimento` — recebimento parcial idempotente (custo médio)

### Inventário
- `POST /api/v1/inventarios` · `POST /api/v1/inventarios/{id}/contagem`
- `POST /api/v1/inventarios/{id}/fechar` — ajustes + baixa reversa automática

### Pedidos & Cozinha
- `POST/GET /api/v1/pedidos` · `POST /api/v1/pedidos/{id}/confirmar`
- `PATCH /api/v1/pedidos/{id}/status` — transições: received→confirmed→preparing→ready→delivered→completed
- `POST /api/v1/pedidos/{id}/cancelar` — baixa reversa idempotente
- `GET /api/v1/pedidos/{id}/eventos` · `GET /api/v1/cozinha/fila` (KDS)

### Storefront Público (Cardápio & Checkout)
- `GET /api/v1/public/{slug}/cardapio` — loja + categorias + produtos + modificadores
- `GET /api/v1/public/{slug}/cep/{cep}` — ViaCEP lookup
- `GET /api/v1/public/{slug}/entrega?cep=` — estimativa (zona, taxa, mínimo, ETA)
- `POST /api/v1/public/{slug}/pedidos` — checkout público (cash, idempotência, taxa por zona)
- `GET /api/v1/public/{slug}/pedidos/{code}` — acompanhamento público

### Zonas de Entrega (Admin)
- `POST/GET/PATCH /api/v1/zonas` — CRUD + validação `cep_ranges` (8 dígitos, start ≤ end)

## Make Targets

| Target | Descrição |
|--------|-----------|
| `make install` | Instala deps (backend `.venv` + frontend `npm ci`) |
| `make up` | Sobe PostgreSQL 16 + Redis |
| `make migrate` | Aplica migrações Alembic (schema + RLS) |
| `make seed` | Popula tenant demo (idempotente) |
| `make dev-backend` | Roda API em `http://localhost:8000` |
| `make dev-frontend` | Roda admin Vite em `http://localhost:5173` (proxy `/api` → backend) |
| `make test` | Backend pytest (testcontainers) + Frontend vitest |
| `make lint` | `ruff check .` + `mypy .` + `biome check .` |
| `make typecheck` | `mypy .` (backend) + `tsc -b --noEmit` (frontend) |

## Testes e Qualidade

```bash
# Tudo
make test
make lint

# Backend apenas
cd backend && ../.venv/bin/pytest -q
cd backend && ../.venv/bin/ruff check .
cd backend && ../.venv/bin/mypy .

# Frontend apenas
cd frontend && npm test
cd frontend && npm run lint
cd frontend && npm run typecheck
```

**Resultados atuais:**
- Backend: 112 testes ✅ · ruff ✅ · mypy ✅ (87 arquivos)
- Frontend: 25 testes ✅ · biome ✅ (55 arquivos) · build ✅

## Arquitetura & Multi-tenant

- **RLS no Postgres**: todas as tabelas de negócio têm policy `tenant_isolation USING (tenant_id = current_setting('app.tenant_id')::uuid)`
- **Middleware FastAPI**: lê `tenant_id` do JWT → `SET app.current_tenant` por conexão
- **Role `stockchef_app`**: sem `BYPASSRLS` — isolamento garantido no banco
- **Tabelas sem RLS**: `tenants`, `plans`, `users`, `refresh_tokens` (escopo identidade)

## Fatias Implementadas

| Fatia | Escopo | Status |
|-------|--------|--------|
| **Fatia 1** | Scaffold, DB, Alembic, RLS, Auth, Insumos, Produtos, Ficha, Pedidos, Outbox, Margem, Seed, Frontend base | ✅ |
| **Fatia 2** | Estoque (custo médio, perdas, movimentos, inventário), Compras (fornecedores, sugestão, PO, recebimento), Frontend admin | ✅ |
| **Fatia 3** | Pedidos avançados (status machine, cancelamento reversível), KDS (fila cozinha), Frontend (comanda, polling) | ✅ |
| **Fatia 4 (E04)** | Cardápio público, ViaCEP, taxa por zona, checkout PWA, pedido público, zonas admin, RegisterPage, Login email-first | ✅ |

## Fluxo de Autenticação (Email-First)

```
1. Usuário digita EMAIL → POST /auth/tenants-by-email
2. Se 1 tenant → vai direto p/ SENHA
3. Se N tenants → mostra lista p/ escolher → SENHA
4. Se 0 → "Email não cadastrado" + link p/ /register
```

Registro (`/register`): nome do restaurante → slug auto + nome + email + senha → cria tenant + loja + owner + auto-login.

## Estrutura do Projeto

```
delivery-project/
├── backend/
│   ├── app/
│   │   ├── core/           # config, db, errors, tenant middleware, deps
│   │   ├── modules/
│   │   │   ├── identity/   # auth, tenants, users, refresh_tokens
│   │   │   ├── catalog/    # insumos, produtos, fichas, adicionais
│   │   │   ├── inventory/  # stock_levels, movements, losses, inventories
│   │   │   ├── purchasing/ # suppliers, POs, suggestions, receipts
│   │   │   ├── orders/     # orders, items, events, status machine, outbox
│   │   │   ├── delivery/   # zones, resolve_zone
│   │   │   └── storefront/ # public cardápio, ViaCEP, public orders
│   │   └── main.py
│   ├── alembic/            # migrations (0001 schema+RLS, 0002 constraints)
│   ├── scripts/seed.py     # tenant demo idempotente
│   └── tests/              # integração (testcontainers) + unit
├── frontend/
│   ├── src/
│   │   ├── api/            # client, public, types
│   │   ├── auth/           # AuthContext, LoginPage, RegisterPage
│   │   ├── cart/           # CartContext (localStorage per slug)
│   │   ├── components/     # ModifierDialog, UI base
│   │   ├── pages/
│   │   │   ├── public/     # Cardapio, Carrinho, Checkout, PedidoPublico
│   │   │   ├── admin/      # Insumos, Produtos, Estoque, Compras, Pedidos, Zonas
│   │   │   └── Dashboard
│   │   └── test/           # vitest + testing-library
│   └── ...
├── docs/superpowers/       # specs, plans, ledger
└── docker-compose.yml      # postgres + redis + backend + frontend
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):
- **Backend job**: ruff + mypy + pytest (PostgreSQL testcontainers)
- **Frontend job**: typecheck + biome lint + vitest + build
- **Compose smoke**: `docker compose up` → health checks API + frontend

## Variáveis de Ambiente

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DATABASE_URL` | URL app (role `stockchef_app`) | `postgresql+psycopg://stockchef_app:stockchef_app@localhost:5432/stockchef` |
| `ALEMBIC_DATABASE_URL` | URL migrações (role `stockchef`) | `postgresql+psycopg://stockchef:stockchef@localhost:5432/stockchef` |
| `JWT_SECRET` | Chave assinatura access token | (gerada no seed) |
| `REFRESH_TOKEN_TTL_DAYS` | Expiração refresh token | `7` |
| `COOKIE_SECURE` | Secure cookie (HTTPS) | `false` |

## Dívidas Técnicas Documentadas

| Item | Local | Impacto |
|------|-------|---------|
| `Zone` não em `app/models.py` | `backend/app/models.py` | Nenhum |
| `create_zone` aceita `store_id` sem validação de posse | `delivery/routes.py` | Mitigado por RLS |
| Busca cardápio `q` sem escape wildcard | `storefront/service.py:58` | Baixo (frontend filtra client-side) |
| Idempotência: race 2 POSTs concorrentes → 500 | `storefront/service.py` | Fora de escopo (PWA single-user) |
| Frontend `ZoneCreate` type diverge backend | `types.ts` | Não usado |
| Prep time não entra no ETA (spec vs test) | `storefront/service.py` | Decidido: manter test behavior |

## Próximos Passos (Roadmap)

1. **Dashboard real** — métricas, alertas, links rápidos
2. **PWA** — service worker, manifest, offline cart sync
3. **Multi-loja admin** — CRUD stores, config delivery/pickup por loja
4. **Testes E2E Playwright** — fluxos críticos ponta a ponta
5. **Monitoring** — logs estruturados, metrics Prometheus, health checks ricos

## Licença

Proprietário — StockChef.