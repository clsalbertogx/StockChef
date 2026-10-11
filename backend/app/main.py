from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.api import api_router
from app.core.errors import register_exception_handlers
from app.core.tenant import install_tenant_middleware
from app.modules.catalog.routes import router as catalog_router
from app.modules.dashboard import router as dashboard_router
from app.modules.delivery.routes import router as delivery_router
from app.modules.identity.routes import router as auth_router
from app.modules.inventory.routes import router as inventory_router
from app.modules.orders.routes import router as orders_router
from app.modules.purchasing.routes import router as purchasing_router
from app.modules.storefront.routes import router as storefront_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="StockChef API", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)
    install_tenant_middleware(app)

    @api_router.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    app.include_router(auth_router, prefix="/api/v1/auth")
    app.include_router(catalog_router, prefix="/api/v1")
    app.include_router(delivery_router, prefix="/api/v1")
    app.include_router(storefront_router, prefix="/api/v1")
    app.include_router(dashboard_router, prefix="/api/v1")
    app.include_router(inventory_router, prefix="/api/v1")
    app.include_router(orders_router, prefix="/api/v1")
    app.include_router(purchasing_router, prefix="/api/v1")
    return app


app = create_app()
