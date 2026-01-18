"""Pydantic schemas for authentication."""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Schema for JWT token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for user information response."""

    id: uuid.UUID
    email: str
    subdomain: str | None
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubdomainClaim(BaseModel):
    """Schema for claiming a subdomain."""

    subdomain: str = Field(..., min_length=3, max_length=20, pattern=r"^[a-z0-9-]+$")


class SubdomainCheckResponse(BaseModel):
    """Schema for subdomain availability check response."""

    subdomain: str
    available: bool
    reason: str | None = None
