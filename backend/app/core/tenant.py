from __future__ import annotations

from uuid import UUID

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.modules.identity.security import decode_access_token


class Actor(BaseModel):
    id: UUID
    tenant_id: UUID
    role: str


def install_tenant_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def tenant_scope(request: Request, call_next):
        header = request.headers.get("Authorization", "")
        if header.lower().startswith("bearer "):
            try:
                payload = decode_access_token(header.split(" ", 1)[1])
                request.state.actor = Actor(
                    id=UUID(payload["sub"]),
                    tenant_id=UUID(payload["tenant_id"]),
                    role=payload["role"],
                )
            except (jwt.PyJWTError, KeyError, TypeError, ValueError):
                return JSONResponse(
                    status_code=401,
                    content={
                        "detail": "Token inválido ou expirado.",
                        "code": "invalid_token",
                    },
                )
        else:
            request.state.actor = None

        actor = request.state.actor
        xt = request.headers.get("X-Tenant-Id")
        if actor is not None and xt is not None and str(actor.tenant_id) != xt:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": "Tenant do cabeçalho não confere com o token.",
                    "code": "tenant_mismatch",
                },
            )
        return await call_next(request)
