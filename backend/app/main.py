from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.api import api_router
from app.core.errors import register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="StockChef API", version="0.1.0", lifespan=lifespan)
    register_exception_handlers(app)

    @api_router.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router)
    return app


app = create_app()
