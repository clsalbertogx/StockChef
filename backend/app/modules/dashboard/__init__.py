from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.tenant import Actor
from app.modules.catalog.models import Ingredient, Product, StockLevel, Unit
from app.modules.orders.models import Customer, Order, OrderItem
from app.modules.purchasing.models import PurchaseOrder

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumo")
def dashboard_resumo(
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
) -> dict:
    """Retorna métricas consolidadas para o dashboard."""
    tid = actor.tenant_id
    now = datetime.now(UTC)
    hoje_inicio = now.replace(hour=0, minute=0, second=0, microsecond=0)
    ontem_inicio = hoje_inicio - timedelta(days=1)
    mes_inicio = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Pedidos hoje ---
    pedidos_hoje = db.scalar(
        select(func.count(Order.id)).where(
            Order.tenant_id == tid,
            Order.created_at >= hoje_inicio,
        )
    ) or 0

    pedidos_ontem = db.scalar(
        select(func.count(Order.id)).where(
            Order.tenant_id == tid,
            Order.created_at >= ontem_inicio,
            Order.created_at < hoje_inicio,
        )
    ) or 0

    # --- Faturamento hoje ---
    faturamento_hoje = db.scalar(
        select(func.coalesce(func.sum(Order.total), Decimal("0"))).where(
            Order.tenant_id == tid,
            Order.created_at >= hoje_inicio,
            Order.status.in_(["confirmed", "preparing", "ready", "delivered", "completed"]),
        )
    ) or Decimal("0")

    faturamento_mes = db.scalar(
        select(func.coalesce(func.sum(Order.total), Decimal("0"))).where(
            Order.tenant_id == tid,
            Order.created_at >= mes_inicio,
            Order.status.in_(["confirmed", "preparing", "ready", "delivered", "completed"]),
        )
    ) or Decimal("0")

    # --- Ticket médio hoje ---
    ticket_medio_hoje = (
        (faturamento_hoje / pedidos_hoje).quantize(Decimal("0.01"))
        if pedidos_hoje > 0 else Decimal("0")
    )

    # --- Pedidos por status ---
    status_counts = db.execute(
        select(Order.status, func.count(Order.id))
        .where(Order.tenant_id == tid)
        .group_by(Order.status)
    ).all()
    pedidos_por_status = {st: count for st, count in status_counts}

    # --- Estoque crítico ---
    estoque_critico = db.execute(
        select(Ingredient.name, StockLevel.quantity, Ingredient.minimum_stock, Unit.symbol)
        .join(StockLevel, StockLevel.ingredient_id == Ingredient.id)
        .join(Unit, Unit.id == Ingredient.base_unit_id)
        .where(
            Ingredient.tenant_id == tid,
            Ingredient.status == "active",
            StockLevel.quantity <= Ingredient.minimum_stock,
        )
        .order_by(StockLevel.quantity)
        .limit(10)
    ).all()

    # --- Pedidos aguardando confirmação (received) ---
    pedidos_aguardando = pedidos_por_status.get("received", 0)

    # --- Pedidos em preparo ---
    pedidos_preparando = pedidos_por_status.get("preparing", 0)

    # --- Pedidos prontos ---
    pedidos_prontos = pedidos_por_status.get("ready", 0)

    # --- Clientes ativos (últimos 30 dias) ---
    trinta_dias_atras = now - timedelta(days=30)
    clientes_ativos = db.scalar(
        select(func.count(func.distinct(Order.customer_id))).where(
            Order.tenant_id == tid,
            Order.created_at >= trinta_dias_atras,
        )
    ) or 0

    # --- Produtos mais vendidos (último mês) ---
    top_produtos = db.execute(
        select(Product.name, func.sum(OrderItem.quantity).label("total_qty"))
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Product.tenant_id == tid,
            Order.created_at >= mes_inicio,
            Order.status.in_(["confirmed", "preparing", "ready", "delivered", "completed"]),
        )
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    ).all()

    # --- Fornecedores pendentes (POs não recebidos) ---
    pos_pendentes = db.scalar(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.tenant_id == tid,
            PurchaseOrder.status.in_(["draft", "sent", "partially_received"]),
        )
    ) or 0

    variacao = (
        round(((pedidos_hoje - pedidos_ontem) / pedidos_ontem * 100), 1)
        if pedidos_ontem > 0 else 0
    )

    return {
        "periodo": {
            "hoje_inicio": hoje_inicio.isoformat(),
            "mes_inicio": mes_inicio.isoformat(),
        },
        "pedidos": {
            "hoje": pedidos_hoje,
            "ontem": pedidos_ontem,
            "variacao_pct": variacao,
        },
        "faturamento": {
            "hoje": str(faturamento_hoje),
            "mes": str(faturamento_mes),
            "ticket_medio_hoje": str(ticket_medio_hoje),
        },
        "pedidos_por_status": pedidos_por_status,
        "alertas": {
            "estoque_critico": [
                {"nome": name, "quantidade": str(qty), "minimo": str(min_stock), "unidade": symbol}
                for name, qty, min_stock, symbol in estoque_critico
            ],
            "pedidos_aguardando": pedidos_aguardando,
            "pedidos_preparando": pedidos_preparando,
            "pedidos_prontos": pedidos_prontos,
            "pos_pendentes": pos_pendentes,
        },
        "clientes_ativos_30d": clientes_ativos,
        "top_produtos": [
            {"nome": name, "quantidade": int(qty)} for name, qty in top_produtos
        ],
    }


@router.get("/pedidos-recentes")
def pedidos_recentes(
    limit: int = 10,
    db: Session = Depends(get_tenant_db),  # noqa: B008
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
) -> list[dict]:
    """Últimos pedidos para lista rápida no dashboard."""
    tid = actor.tenant_id
    rows = db.execute(
        select(Order.code, Order.status, Order.total, Order.created_at, Customer.name)
        .join(Customer, Customer.id == Order.customer_id)
        .where(Order.tenant_id == tid)
        .order_by(Order.created_at.desc())
        .limit(limit)
    ).all()
    return [
        {
            "codigo": code,
            "status": st,
            "total": str(total),
            "criado_em": criado.isoformat(),
            "cliente": cliente,
        }
        for code, st, total, criado, cliente in rows
    ]