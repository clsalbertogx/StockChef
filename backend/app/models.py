"""Registro central de modelos — cada módulo importado aqui popula o metadata."""
from app.core.db import Base as Base
from app.modules.catalog.models import (  # noqa: F401
    Category,
    Ingredient,
    Product,
    Recipe,
    RecipeItem,
    StockLevel,
    StockMovement,
    Store,
    Supplier,
    Unit,
)
from app.modules.identity.models import RefreshToken, Tenant, User  # noqa: F401
from app.modules.inventory.models import (  # noqa: F401
    InventoryCount,
    InventoryCountItem,
    Loss,
)
from app.modules.orders.models import (  # noqa: F401
    Customer,
    Order,
    OrderEvent,
    OrderItem,
    OutboxEvent,
)
from app.modules.purchasing.models import (  # noqa: F401
    GoodsReceipt,
    GoodsReceiptItem,
    PurchaseOrder,
    PurchaseOrderItem,
)

metadata = Base.metadata
