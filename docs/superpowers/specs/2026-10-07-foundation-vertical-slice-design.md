# Design: Fundação do repo + primeira fatia vertical (StockChef)

**Data:** 2026-10-07
**Status:** Aprovado (design em chat) — aguardando revisão do usuário
**Escopo:** primeiras 1–2 semanas de implementação; substitui W3 + W4 do plano de 4 semanas (`docs/backlog-delivery-project.md:1547-1607`) com ajustes de escopo acordados.

## 1. Objetivo

Transformar o repositório vazio (apenas `docs/`, zero commits) em uma base de código funcioneira que demonstre o fluxo núcleo do StockChef ponta a ponta, via API:

> criar insumo → produto → ficha técnica → pedido → confirmação → baixa de estoque idempotente → leitura de custo/margem

Fora de escopo desta fatia (explicitamente):
- PWA do cliente, cardápio, carrinho, checkout
- Pagamentos (Pix/cartão), PSP
- RabbitMQ (contrato de evento preparado, broker entra depois)
- Motorista/entrega, analytics, agentes de IA, billing
- Visual final baseado em `docs/images/` (só funcionalidade básica no admin)
- Offline-first / WatermelonDB

## 2. Decisões aprovadas

| Decisão | Escolha |
|---|---|
| Estrutura | Monorepo com apps isolados (`backend/`, `frontend/`, `infra/`) — abordagem A |
| Admin web | Vite + React + TypeScript (não Next.js) |
| Lint/format JS/TS | **Biome** (não ESLint) |
| Assincronismo | Síncrono-in-processo primeiro: outbox table + `asyncio` worker; RabbitMQ depois |
| Migrações | Alembic desde o dia 1; DDL do backlog (`docs/backlog-delivery-project.md:262-1013`) como base do `0001_initial` — nunca `create_all` |
| Backend | Python + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + psycopg |
| DB | PostgreSQL 16 (compose local + serviço no CI), RLS para isolamento de tenant |

## 3. Estrutura do repositório

```
delivery-project/
├── .gitignore
├── README.md                 # aponta docs/ como fonte de verdade
├── docker-compose.yml        # postgres:16 + redis (dev)
├── .github/workflows/ci.yml
├── backend/
│   ├── pyproject.toml        # fastapi, sqlalchemy, alembic, pydantic, psycopg,
│   │                         # pytest, ruff, mypy, testcontainers
│   ├── alembic.ini
│   ├── alembic/              # env.py + versions/0001_initial
│   ├── scripts/seed.py       # tenant demo
│   └── app/
│       ├── main.py           # app factory, router /health
│       ├── core/             # config, db, security (JWT), tenant middleware, deps
│       ├── modules/
│       │   ├── identity/     # auth, tenants, users
│       │   ├── catalog/      # insumos, produtos, fichas técnicas
│       │   ├── orders/       # pedidos, outbox, handlers
│       │   └── inventory/    # stock_levels, stock_movements
│       └── tests/
│           ├── unit/
│           └── integration/
└── frontend/
    ├── package.json
    ├── biome.json
    └── src/
```

Cada app tem manifest de dependências próprio; sem tooling de workspace (YAGNI).

## 4. Fundação e CI

- `docker-compose.yml`: Postgres 16 e Redis para desenvolvimento local.
- CI (GitHub Actions), jobs separados, em PR e push para `main`:
  - **backend**: Postgres 16 como serviço → `ruff check` → `mypy` → `pytest`
  - **frontend**: `biome check` → `tsc --noEmit` → `vitest run` → `build`
- Primeiro commit inclui `.gitignore`, README e scaffold.

## 5. Auth, multi-tenancy e RLS

**Modelo (tabelas `identity` do backlog):** `tenants`, `users` (FK → tenant), `refresh_tokens`.

**Fluxo:**
- `POST /api/v1/auth/register` — cria tenant + usuário `owner` em transação única
- `POST /api/v1/auth/login` — access token JWT (30 min, claims: `sub`, `tenant_id`, `role`) + refresh token (httpOnly cookie, 7 dias)
- Roles: `owner` | `manager` | `staff` (uso das roles além de owner fica para depois; o campo existe desde já)

**Isolamento em 3 camadas:**
1. Middleware FastAPI lê `tenant_id` do JWT → `Request.state`
2. Session SQLAlchemy executa `SET app.current_tenant = '<uuid>'` por conexão
3. RLS no Postgres: `tenant_id = current_setting('app.current_tenant')::uuid` nas tabelas de negócio (orders, order_items, stock_levels, stock_movements, outbox_events, recommendations, etc.)

**Regras:**
- Role da aplicação **sem** `BYPASSRLS`; role de migrations separada **com** privilégio de bypass
- Registro de tenant novo faz seed de tabelas auxiliares com escopo do tenant na mesma transação
- Login/crédenciais em tenant divergente → resposta 404 genérica (não vaza existência)
- Cenário Gherkin de isolamento (`docs/backlog-delivery-project.md:103`) vira teste automatizado de integração

## 6. Vertical slice — API

Todos os endpoints sob `/api/v1`, autenticados, tenant via JWT.

### 6.1 Catálogo
- `POST/GET/PATCH /insumos` — unidade, custo médio ponderado, saldo inicial (grava `stock_levels`)
- `POST/GET /produtos` — produto final com preço
- `POST/GET /produtos/{id}/ficha-tecnica` — associa insumo + quantidade; ao salvar recalcula custo do produto

### 6.2 Pedidos
- `POST /pedidos` — status `PENDING`; valida disponibilidade de estoque
- `POST /pedidos/{id}/confirmar` — transação: valida → status `CONFIRMADO` → grava `order_events` → grava evento `order.confirmed` em `outbox_events` → agenda task pós-commit

### 6.3 Baixa de estoque idempotente
- Worker in-process (`asyncio.create_task` pós-commit) drena a `outbox_events`:
  - event_id como PK lógico → reprocessar é no-op
  - decrementa `stock_levels` transacionalmente (`UPDATE ... WHERE quantidade >= qtd`), grava `stock_movements`
- Saldo insuficiente **não bloqueia a venda**: pedido fica `CONFIRMADO_COM_PENDÊNCIA` + alerta (regra do plano: venda nunca é barrada por estoque)
- `GET /pedidos/{id}/eventos` — observabilidade mínima do outbox

### 6.4 Custo e margem
- `GET /produtos/{id}/margem` — custo da ficha (Σ insumo × custo médio) vs preço; margem % e R$

### 6.5 Erros
- Estoque indisponível na criação → 422 com detalhe do insumo faltante
- Handler global FastAPI padronizado `{detail, code}`
- Evento sem processamento visível → status `PENDING` no outbox exposto em eventos do pedido

### 6.6 Seed
- `make seed`: tenant demo com 2 insumos, 1 produto (hambúrguer), ficha técnica e 1 pedido — fluxo testável em 1 minuto

## 7. Frontend admin

- Stack: Vite + React + TS + Tailwind + **shadcn/ui** + TanStack Query
- Rotas: `/login`, dashboard simples, `/insumos`, `/produtos` (com editor de ficha técnica), `/pedidos` (lista + detalhe com "Confirmar")
- Cliente API com interceptor de token e refresh automático
- Visual: funcional, seguindo a palette/densidade do design system; polimento baseado em `docs/images/` fica para iteracao posterior
- Sem PWA/offline nesta fatia

## 8. Testes

| Camada | Ferramenta | Conteúdo |
|---|---|---|
| Unit backend | pytest | custo de ficha, margem, idempotência do handler, validação de estoque |
| Integração backend | pytest + Postgres real (testcontainers/CI) | registro + isolamento RLS, fluxo completo criar→confirmar→baixa, reprocessamento idempotente |
| Frontend | Vitest + Testing Library | login, confirmar pedido |
| Tipos/lint | mypy, ruff, tsc, biome | no CI |

**Critério de saída da fatia:** `make test` verde local + CI verde no GitHub Actions + fluxo do seed percorrido ponta a ponta via API.

## 9. Ordem de implementação

1. Scaffold repo + compose + README + `.gitignore` + CI vazio → primeiro commit
2. Alembic + `0001_initial` (DDL do backlog, tabela a tabela, índices + policies RLS)
3. Auth + tenant middleware + RLS + teste de isolamento
4. Catálogo: insumo → produto → ficha técnica (+ testes de custo)
5. Pedidos + outbox + baixa idempotente (+ testes de idempotência)
6. Endpoint de margem + seed
7. Frontend admin dos 4 fluxos
8. CI completa (ruff/mypy/pytest/biome/tsc/vitest) + README final

## 10. Riscos e mitigações

- **DDL do backlog pode ter divergências** vs. o modelo lido dos RFs → revisar tabela a tabela durante a migração 0001; corrigir no spec se necessário
- **RLS quebra queries legadas** (ex.: jobs com superuser) → role da app nunca usa bypass; testes de integração cobrem
- **Outbox in-process perde eventos se o processo cair** → aceito nesta fatia (evento pendente fica visível); RabbitMQ/worker dedicado resolve na Fase 2+
- **Escopo crescer** (PWA, pagamentos tentam entrar) → lista de fora-de-escopo na Seção 1 é vinculante

## 11. Referências

- Plano 4 semanas: `docs/backlog-delivery-project.md:1547-1607`
- DDL: `docs/backlog-delivery-project.md:262-1013`
- Gherkin de isolamento: `docs/backlog-delivery-project.md:103-260`
- Critérios de aceite do MVP: `docs/plan-delivery-project.md:1632`
- ADRs: `docs/plan-delivery-project.md:1796`
