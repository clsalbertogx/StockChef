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

metadata = Base.metadata
