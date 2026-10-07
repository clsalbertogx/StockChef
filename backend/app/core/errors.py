from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        extra: dict | None = None,
    ) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.http_status = http_status
        self.extra = extra or {}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def on_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
        )
