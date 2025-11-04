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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from models import User
from models.enums import UserRole
from schemas.auth import (
    AccessToken,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserInfo,
)

router = APIRouter(tags=["Auth"])


@router.post(
    "/register",
    response_model=TokenPair,
    status_code=201,
    summary="Register a new user",
    description="""
Create a new **reader** account in the BookDrop system.

The endpoint:
- Normalizes and lowercases the provided email.
- Hashes the password using Argon2.
- Returns a pair of JWT tokens (`access_token` and `refresh_token`).

**Default role:** `reader`
""",
    responses={
        201: {"description": "User registered successfully."},
        400: {"description": "Email already registered."},
        422: {"description": "Validation error in input data."},
    },
)
async def register_user(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and return JWT tokens."""
    existing = await db.execute(
        select(User).where(User.email == str(payload.email).lower().strip())
    )
    if existing.scalar():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=str(payload.email).lower().strip(),
        password=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        role=UserRole.READER,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)
    await db.commit()

    data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    return TokenPair(
        access_token=create_access_token(data), refresh_token=create_refresh_token(data)
    )


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in with email and password",
    description="""
Authenticate a user using email and password.

If successful, returns a new pair of tokens:
- `access_token` — short-lived token for API access.
- `refresh_token` — long-lived token for obtaining new access tokens.
""",
    responses={
        200: {"description": "Login successful."},
        401: {"description": "Invalid email or password."},
    },
)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(select(User).where(User.email == str(payload.email).lower().strip()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, str(user.password)):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    data = {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }

    return TokenPair(
        access_token=create_access_token(data), refresh_token=create_refresh_token(data)
    )


@router.post(
    "/refresh",
    response_model=AccessToken,
    summary="Refresh access token",
    description="""
Exchange a valid **refresh token** for a new **access token**.

Use this endpoint when the access token expires but the refresh token is still valid.
""",
    responses={
        200: {"description": "Access token refreshed successfully."},
        401: {"description": "Invalid or expired refresh token."},
    },
)
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


@router.get(
    "/me",
    response_model=UserInfo,
    summary="Get current user info",
    description="""
Retrieve details of the currently authenticated user.

Requires a valid **Bearer access token** in the `Authorization` header.
""",
    responses={
        200: {"description": "User information returned successfully."},
        401: {"description": "Missing or invalid access token."},
    },
)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return information about the currently logged-in user."""
    return UserInfo(
        id=UUID(str(current_user.id)),
        email=current_user.email,
        role=current_user.role,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
    )


@router.post(
    "/logout",
    summary="Log out (stateless)",
    description="""
Perform a stateless logout.

BookDrop does not maintain server-side sessions.
Clients must remove JWT tokens locally (from browser storage, mobile app, etc.).
""",
    responses={200: {"description": "Logout acknowledged by the server."}},
)
async def logout():
    """Perform stateless logout — client must delete tokens locally."""
    return {"detail": "Logout successful. Tokens must be deleted client-side."}
