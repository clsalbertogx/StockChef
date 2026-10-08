from __future__ import annotations

import sqlalchemy.exc
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


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

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Dados inválidos.",
                "code": "validation_error",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(sqlalchemy.exc.IntegrityError)
    async def on_integrity_error(
        request: Request, exc: sqlalchemy.exc.IntegrityError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Conflito de dados.", "code": "conflict"},
        )

    @app.exception_handler(Exception)
    async def on_error(request: Request, exc: Exception) -> JSONResponse:
        # Não interceptar HTTPException (404/405 etc.) ou os handlers acima.
        handler = request.app.exception_handlers.get(StarletteHTTPException)
        if isinstance(exc, StarletteHTTPException) and handler is not None:
            return await handler(request, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno.", "code": "internal_error"},
        )