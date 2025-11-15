# === tests/api/librarian/test_list_orders.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Order, User
from models.enums import OrderStatus, UserRole


@pytest.mark.asyncio
async def test_list_orders_returns_all_orders(client: AsyncClient, db_session: AsyncSession):
    """Should return a list of all orders when called by a librarian."""
    # Arrange: create librarian
    librarian = User(
        email="lib1@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib",
        last_name="One",
    )

    # Create two readers + orders
    reader1 = User(
        email="reader1@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="R1",
        last_name="User",
    )
    reader2 = User(
        email="reader2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="R2",
        last_name="User",
    )

    db_session.add_all([librarian, reader1, reader2])
    await db_session.commit()
    await db_session.refresh(librarian)
    await db_session.refresh(reader1)
    await db_session.refresh(reader2)

    o1 = Order(reader_id=reader1.id, status=OrderStatus.NEW)
    o2 = Order(reader_id=reader2.id, status=OrderStatus.PREPARED)

    db_session.add_all([o1, o2])
    await db_session.commit()

    # Act
    res = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
    )

    # Assert
    assert res.status_code == 200
    data = res.json()

    assert isinstance(data, list)
    assert len(data) == 2

    ids = {entry["order_id"] for entry in data}
    assert str(o1.id) in ids
    assert str(o2.id) in ids


@pytest.mark.asyncio
async def test_list_orders_returns_empty_list_if_no_orders(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return an empty list when no orders exist."""
    librarian = User(
        email="noliborders@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib",
        last_name="Zero",
    )
    db_session.add(librarian)
    await db_session.commit()
    await db_session.refresh(librarian)

    res = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
    )

    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_orders_fails_if_not_librarian(client: AsyncClient, db_session: AsyncSession):
    """Should return 403 when user is authenticated but not a librarian."""
    reader = User(
        email="reader-not-lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Not",
        last_name="Lib",
    )
    db_session.add(reader)
    await db_session.commit()
    await db_session.refresh(reader)

    res = await client.get(
        "/api/librarian/orders",
        headers={"Authorization": f"Bearer test-{reader.id}"},
    )

    assert res.status_code == 403
    assert "librarian" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_orders_unauthorized(client: AsyncClient):
    """Should return 401 when no token is provided."""
    res = await client.get("/api/librarian/orders")
    assert res.status_code == 401
