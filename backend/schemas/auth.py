# === schemas/auth.py ===

from uuid import UUID

from pydantic import BaseModel, EmailStr, constr


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: constr(min_length=8)
    first_name: constr(min_length=1, max_length=100)
    last_name: constr(min_length=1, max_length=100)


class LoginRequest(BaseModel):
    """Request model for user login."""

    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    """Request model for refreshing JWT tokens."""

    refresh_token: str


class TokenPair(BaseModel):
    """Response model containing access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessToken(BaseModel):
    """Response model containing only an access token."""

    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    """Response model for basic user information."""

    id: UUID
    email: EmailStr
    role: str
    first_name: str
    last_name: str
