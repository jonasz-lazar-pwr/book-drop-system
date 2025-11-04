# === tests/api/auth/test_register.py ===

import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """Test that a new user can register successfully."""
    payload = {
        "email": "reader@example.com",
        "password": "StrongPass123",
        "first_name": "Alice",
        "last_name": "Reader",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201, response.text

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    """Test that registering with an existing email returns HTTP 400."""
    payload = {
        "email": "dup@example.com",
        "password": "AnotherPass123",
        "first_name": "John",
        "last_name": "Doe",
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201, first.text

    duplicate = await client.post("/auth/register", json=payload)
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    """Test that an invalid email returns HTTP 422."""
    payload = {
        "email": "not-an-email",
        "password": "ValidPass123",
        "first_name": "A",
        "last_name": "B",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """Test that a weak (too short) password returns validation error."""
    payload = {
        "email": "weak@example.com",
        "password": "123",
        "first_name": "A",
        "last_name": "B",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_trims_and_lowercases_email(client: AsyncClient):
    """Test that email is stored in lowercase and trimmed of spaces."""
    payload = {
        "email": "  Reader2@Example.COM  ",
        "password": "StrongPass123",
        "first_name": "Alice",
        "last_name": "Reader",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    tokens = response.json()
    assert "access_token" in tokens

    # Second registration attempt with lowercase email should trigger duplicate check
    duplicate = await client.post(
        "/auth/register",
        json={
            "email": "reader2@example.com",
            "password": "StrongPass123",
            "first_name": "Alice",
            "last_name": "Reader",
        },
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"
