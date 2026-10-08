from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    tenant_name: str = Field(min_length=2, max_length=120)
    tenant_slug: str = Field(min_length=2, max_length=60, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    name: str = Field(min_length=2, max_length=120)


class LoginRequest(BaseModel):
    tenant_slug: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    name: str
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MeOut(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
