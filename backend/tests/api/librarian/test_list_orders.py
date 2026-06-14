"""Tests for GET /api/librarian/orders endpoint."""

from datetime import datetime, timedelta

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Order, User
from models.enums import OrderStatus


@pytest.mark.asyncio
async def test_list_orders_success(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test successful listing of orders."""
    # Create test orders
    order1 = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    order2 = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    order3 = Order(reader_id=reader_user.id, status=OrderStatus.RETURNED)

    db_session.add_all([order1, order2, order3])
    await db_session.commit()

    # List orders
    response = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 3

    # Verify structure
    first_order = data[0]
    assert "order_id" in first_order
    assert "reader_id" in first_order
    assert "reader_email" in first_order
    assert "reader_first_name" in first_order
    assert "reader_last_name" in first_order
    assert "status" in first_order
    assert "created_at" in first_order

    # Verify reader info
    assert first_order["reader_email"] == reader_user.email
    assert first_order["reader_first_name"] == reader_user.first_name
    assert first_order["reader_last_name"] == reader_user.last_name


@pytest.mark.asyncio
async def test_list_orders_empty(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
):
    """Test listing orders when database is empty."""
    response = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_orders_unauthorized(
    client: AsyncClient,
):
    """Test listing orders without authentication."""
    response = await client.get("/api/librarian/orders")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_orders_forbidden_for_reader(
    client: AsyncClient,
    reader_token: str,
):
    """Test that readers cannot access librarian endpoints."""
    response = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403
    assert "librarian" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_orders_sorted_by_date(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test that orders are sorted by creation date (newest first)."""
    # Create orders with different timestamps
    old_order = Order(
        reader_id=reader_user.id,
        status=OrderStatus.NEW,
        created_at=datetime.utcnow() - timedelta(days=2),
    )
    new_order = Order(
        reader_id=reader_user.id,
        status=OrderStatus.NEW,
        created_at=datetime.utcnow(),
    )

    db_session.add_all([old_order, new_order])
    await db_session.commit()
    await db_session.refresh(old_order)
    await db_session.refresh(new_order)

    response = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # First order should be the newest
    assert data[0]["order_id"] == str(new_order.id)
    assert data[1]["order_id"] == str(old_order.id)
