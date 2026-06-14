# tests/api/orders/test_get_user_orders.py

from datetime import datetime, timedelta

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Order, OrderItem, User
from models.enums import OrderStatus, UserRole


@pytest.mark.asyncio
async def test_get_user_orders_returns_all_orders(client: AsyncClient, db_session: AsyncSession):
    """Return all orders for authenticated user."""
    user = User(
        email="reader@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="John",
        last_name="Doe",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create test book
    book = Book(
        isbn="9781234567890",
        title="Test Book",
        authors="Test Author",
    )
    db_session.add(book)
    await db_session.commit()

    book_item = BookItem(isbn=book.isbn, is_available=False)
    db_session.add(book_item)
    await db_session.commit()

    # Create orders with different statuses
    order1 = Order(
        reader_id=user.id,
        status=OrderStatus.READY_FOR_PICKUP,
        created_at=datetime.utcnow(),
    )
    order2 = Order(
        reader_id=user.id,
        status=OrderStatus.PICKED_UP,
        created_at=datetime.utcnow() - timedelta(days=7),
    )
    db_session.add_all([order1, order2])
    await db_session.commit()

    # Add items to orders
    item1 = OrderItem(
        order_id=order1.id,
        book_item_id=book_item.id,
        due_date=datetime.utcnow() + timedelta(days=14),
    )
    db_session.add(item1)
    await db_session.commit()

    res = await client.get(
        "/api/orders",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["status"] in ["ready_for_pickup", "picked_up"]
    assert data[0]["reader_id"] == str(user.id)


@pytest.mark.asyncio
async def test_get_user_orders_with_status_filter(client: AsyncClient, db_session: AsyncSession):
    """Filter orders by status parameter."""
    user = User(
        email="filter@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Filter",
        last_name="Test",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    order1 = Order(
        reader_id=user.id,
        status=OrderStatus.READY_FOR_PICKUP,
    )
    order2 = Order(
        reader_id=user.id,
        status=OrderStatus.PICKED_UP,
    )
    db_session.add_all([order1, order2])
    await db_session.commit()

    res = await client.get(
        "/api/orders?status=ready_for_pickup",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["status"] == "ready_for_pickup"


@pytest.mark.asyncio
async def test_get_user_orders_unauthenticated(client: AsyncClient):
    """Return 401 when no Authorization header provided."""
    res = await client.get("/api/orders")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_user_orders_empty_list(client: AsyncClient, db_session: AsyncSession):
    """Return empty list when user has no orders."""
    user = User(
        email="noorders@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Orders",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    res = await client.get(
        "/api/orders",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 0
