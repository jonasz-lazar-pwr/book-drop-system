# === tests/api/auth/test_login.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy import insert

from core.security import hash_password
from models import User
from models.enums import UserRole


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session):
    """Test that a valid login returns HTTP 200 and a token pair."""
    await db_session.execute(
        insert(User).values(
            email="reader@example.com",
            password=hash_password("StrongPass123"),
            first_name="Alice",
            last_name="Reader",
            role=UserRole.READER,
        )
    )
    await db_session.commit()

    payload = {"email": "reader@example.com", "password": "StrongPass123"}
    response = await client.post("/auth/login", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_invalid_email(client: AsyncClient):
    """Test that login with a non-existent email returns HTTP 401."""
    payload = {"email": "unknown@example.com", "password": "SomePass123"}
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient, db_session):
    """Test that login with an incorrect password returns HTTP 401."""
    await db_session.execute(
        insert(User).values(
            email="user2@example.com",
            password=hash_password("CorrectPass123"),
            first_name="John",
            last_name="Smith",
            role=UserRole.READER,
        )
    )
    await db_session.commit()

    payload = {"email": "user2@example.com", "password": "WrongPass"}
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_case_insensitive_email(client: AsyncClient, db_session):
    """Test that login works regardless of email case sensitivity."""
    await db_session.execute(
        insert(User).values(
            email="caseuser@example.com",
            password=hash_password("CasePass123"),
            first_name="Case",
            last_name="Tester",
            role=UserRole.READER,
        )
    )
    await db_session.commit()

    payload = {"email": "CASEUSER@EXAMPLE.COM", "password": "CasePass123"}
    response = await client.post("/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_missing_fields(client: AsyncClient):
    """Test that login without required fields returns HTTP 422."""
    response = await client.post("/auth/login", json={"email": "a@b.com"})
    assert response.status_code == 422
