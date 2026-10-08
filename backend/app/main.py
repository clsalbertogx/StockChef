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
