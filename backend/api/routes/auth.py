# === api/routes/auth.py ===

"""
Authentication and authorization routes for BookDrop API.

Endpoints:
- POST /auth/register — Register a new user account.
- POST /auth/login — Authenticate and return JWT tokens.
- POST /auth/refresh — Refresh an access token using a valid refresh token.
- GET /auth/me — Retrieve details of the currently authenticated user.
- POST /auth/logout — Stateless logout (client should remove stored tokens).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from models import User
from repositories.auth_repository import AuthRepository
from schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserInfo,
)

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=TokenPair, status_code=201, summary="Register new user")
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT tokens."""
    user = await AuthRepository.register_user(
        db, payload.email, payload.password, payload.first_name, payload.last_name
    )

    data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    return TokenPair(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


@router.post("/login", response_model=TokenPair, summary="Log in")
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    user = await AuthRepository.authenticate_user(db, payload.email, payload.password)

    data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    return TokenPair(
        access_token=create_access_token(data),
        refresh_token=create_refresh_token(data),
    )


@router.post("/refresh", response_model=AccessToken, summary="Refresh access token")
async def refresh_token(payload: RefreshRequest):
    """Generate a new access token using a valid refresh token."""
    decoded = verify_token(payload.refresh_token)
    if not decoded or decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    access_token = create_access_token(
        {
            "id": decoded["sub"],
            "email": decoded["email"],
            "role": decoded["role"],
            "first_name": decoded["first_name"],
            "last_name": decoded["last_name"],
        }
    )

    return AccessToken(access_token=access_token)


@router.get("/me", response_model=UserInfo, summary="Get current user")
async def get_me(current_user: User = Depends(get_current_user)):
    """Return information about the current user."""
    return UserInfo(
        id=UUID(str(current_user.id)),
        email=current_user.email,
        role=current_user.role,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )


@router.post("/logout", summary="Log out")
async def logout():
    """Acknowledge logout and invalidate local tokens client-side."""
    return {"detail": "Logout successful. Tokens must be deleted client-side."}
