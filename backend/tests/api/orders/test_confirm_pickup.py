# tests/api/orders/test_confirm_pickup.py


import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Locker, LockerBox, LockerShipment, Order, OrderItem, User
from models.enums import OrderStatus, ShipmentMode, ShipmentStatus, UserRole


@pytest.mark.asyncio
async def test_confirm_pickup_success(client: AsyncClient, db_session: AsyncSession):
    """Successfully confirm pickup and update status."""
    user = User(
        email="pickup@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Pickup",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    book = Book(isbn="9781234567890", title="Test", authors="Author")
    db_session.add(book)
    await db_session.commit()

    book_item = BookItem(isbn=book.isbn, is_available=False)
    db_session.add(book_item)
    await db_session.commit()

    locker = Locker(
        locker_code="WRO-001",
        street="Test St",
        city="Wroclaw",
        postal_code="50-001",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    locker_box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(locker_box)
    await db_session.commit()

    order = Order(reader_id=user.id, status=OrderStatus.READY_FOR_PICKUP)
    db_session.add(order)
    await db_session.commit()

    order_item = OrderItem(order_id=order.id, book_item_id=book_item.id)
    db_session.add(order_item)

    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=locker_box.id,
        mode=ShipmentMode.DELIVERY,
        status=ShipmentStatus.PLACED_IN_LOCKER,
        pickup_code="ABC12345",
    )
    db_session.add(shipment)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/confirm-pickup",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert "Pickup confirmed" in data["message"]

    # Verify database changes
    await db_session.refresh(order)
    assert order.status == OrderStatus.PICKED_UP
    assert order.updated_at is not None

    await db_session.refresh(shipment)
    assert shipment.status == ShipmentStatus.RETRIEVED_BY_USER

    await db_session.refresh(order_item)
    assert order_item.due_date is not None


@pytest.mark.asyncio
async def test_confirm_pickup_invalid_status(client: AsyncClient, db_session: AsyncSession):
    """Return 400 when order status is not 'ready_for_pickup'."""
    user = User(
        email="wrongstatus@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Wrong",
        last_name="Status",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    order = Order(reader_id=user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/confirm-pickup",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "Cannot confirm pickup" in res.json()["detail"]


@pytest.mark.asyncio
async def test_confirm_pickup_not_found(client: AsyncClient, db_session: AsyncSession):
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
    res = await client.post(
        f"/api/orders/{fake_order_id}/confirm-pickup",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_confirm_pickup_access_denied(client: AsyncClient, db_session: AsyncSession):
    """Return 403 when trying to confirm another user's order."""
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

    order = Order(reader_id=user1.id, status=OrderStatus.READY_FOR_PICKUP)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/confirm-pickup",
        headers={"Authorization": f"Bearer test-{user2.id}"},
    )

    assert res.status_code == 403
