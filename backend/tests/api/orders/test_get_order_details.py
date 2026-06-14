# tests/api/orders/test_get_order_details.py

from datetime import datetime, timedelta

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Locker, LockerBox, LockerShipment, Order, OrderItem, User
from models.enums import OrderStatus, ShipmentMode, ShipmentStatus, UserRole


@pytest.mark.asyncio
async def test_get_order_details_success(client: AsyncClient, db_session: AsyncSession):
    """Return full order details with items and shipment."""
    user = User(
        email="details@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Details",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Create book and items
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

    # Create locker
    locker = Locker(
        locker_code="WRO-001",
        street="Test Street 1",
        city="Wroclaw",
        postal_code="50-001",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    locker_box = LockerBox(
        locker_id=locker.id,
        number=1,
        is_available=False,
    )
    db_session.add(locker_box)
    await db_session.commit()

    # Create order
    order = Order(
        reader_id=user.id,
        status=OrderStatus.READY_FOR_PICKUP,
    )
    db_session.add(order)
    await db_session.commit()

    # Add order item
    order_item = OrderItem(
        order_id=order.id,
        book_item_id=book_item.id,
        due_date=datetime.utcnow() + timedelta(days=14),
    )
    db_session.add(order_item)

    # Add shipment
    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=locker_box.id,
        mode=ShipmentMode.DELIVERY,
        status=ShipmentStatus.PLACED_IN_LOCKER,
        pickup_code="ABC12345",
        placed_at=datetime.utcnow(),
    )
    db_session.add(shipment)
    await db_session.commit()

    res = await client.get(
        f"/api/orders/{order.id}",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(order.id)
    assert data["status"] == "ready_for_pickup"
    assert len(data["items"]) == 1
    assert data["items"][0]["isbn"] == book.isbn
    assert data["shipment"] is not None
    assert data["shipment"]["pickup_code"] == "ABC12345"
    assert data["shipment"]["locker"]["locker_code"] == "WRO-001"


@pytest.mark.asyncio
async def test_get_order_details_not_found(client: AsyncClient, db_session: AsyncSession):
    """Return 404 when order does not exist."""
    user = User(
        email="notfound@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Not",
        last_name="Found",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    fake_order_id = "00000000-0000-0000-0000-000000000000"
    res = await client.get(
        f"/api/orders/{fake_order_id}",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 404
    assert "Order not found" in res.json()["detail"]


@pytest.mark.asyncio
async def test_get_order_details_access_denied(client: AsyncClient, db_session: AsyncSession):
    """Return 403 when trying to access another user's order."""
    user1 = User(
        email="user1@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="User",
        last_name="One",
    )
    user2 = User(
        email="user2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="User",
        last_name="Two",
    )
    db_session.add_all([user1, user2])
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    order = Order(
        reader_id=user1.id,
        status=OrderStatus.NEW,
    )
    db_session.add(order)
    await db_session.commit()

    res = await client.get(
        f"/api/orders/{order.id}",
        headers={"Authorization": f"Bearer test-{user2.id}"},
    )

    assert res.status_code == 403
    assert "Access denied" in res.json()["detail"]


@pytest.mark.asyncio
async def test_get_order_details_unauthenticated(client: AsyncClient):
    """Return 401 when no Authorization header provided."""
    fake_order_id = "00000000-0000-0000-0000-000000000000"
    res = await client.get(f"/api/orders/{fake_order_id}")
    assert res.status_code == 401
