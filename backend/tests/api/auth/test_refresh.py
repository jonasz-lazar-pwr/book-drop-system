# === tests/api/auth/test_refresh.py ===

import pytest

from httpx import AsyncClient

from core.security import create_refresh_token, verify_token


@pytest.mark.asyncio
async def test_refresh_token_valid(client: AsyncClient):
    """Test that a valid refresh token generates a new access token."""
    user_data = {
        "id": "11111111-1111-1111-1111-111111111111",
        "email": "reader@example.com",
        "role": "reader",
        "first_name": "Alice",
        "last_name": "Reader",
    }
    refresh_token = create_refresh_token(user_data)

    response = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    decoded = verify_token(data["access_token"])
    assert decoded["sub"] == user_data["id"]
    assert decoded["email"] == user_data["email"]
    assert decoded["type"] == "access"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    """Test that an invalid refresh token returns HTTP 401."""
    response = await client.post("/auth/refresh", json={"refresh_token": "fake.invalid.token"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"
