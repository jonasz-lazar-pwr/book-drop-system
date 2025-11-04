# === tests/api/auth/test_me.py ===

import pytest

from httpx import AsyncClient

from core.security import create_access_token, hash_password
from models import User
from models.enums import UserRole


@pytest.mark.asyncio
async def test_me_endpoint_returns_current_user(client: AsyncClient, db_session):
    """Test that /auth/me returns user data for a valid access token."""
    user = User(
        email="alice@example.com",
        password=hash_password("StrongPass123"),
        first_name="Alice",
        last_name="Reader",
        role=UserRole.READER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    user_data = {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "first_name": user.first_name,
        "last_name": user.last_name,
    }
    token = create_access_token(user_data)
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()

    assert data["email"] == user.email
    assert data["role"] == user.role
    assert data["first_name"] == user.first_name
    assert data["last_name"] == user.last_name


@pytest.mark.asyncio
async def test_me_endpoint_unauthorized(client: AsyncClient):
    """Test that a missing token returns HTTP 401."""
    response = await client.get("/auth/me")
    assert response.status_code == 401
