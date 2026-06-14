# tests/api/orders/test_initiate_return.py

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Locker, LockerBox, Order, User
from models.enums import OrderStatus, UserRole


@pytest.mark.asyncio
async def test_initiate_return_success(client: AsyncClient, db_session: AsyncSession):
    """Successfully initiate return and create shipment."""
    user = User(
        email="return@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Return",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    locker = Locker(
        locker_code="WRO-002",
        street="Return St",
        city="Wroclaw",
        postal_code="50-002",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    locker_box = LockerBox(locker_id=locker.id, number=1, is_available=True)
    db_session.add(locker_box)
    await db_session.commit()

    order = Order(reader_id=user.id, status=OrderStatus.PICKED_UP)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/initiate-return",
        json={"locker_id": str(locker.id)},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["mode"] == "return"
    assert data["status"] == "created"
    assert "pickup_code" in data
    assert len(data["pickup_code"]) == 8
    assert data["locker"]["locker_code"] == "WRO-002"

    # Verify database changes
    await db_session.refresh(order)
    assert order.status == OrderStatus.RETURN_IN_PROGRESS

    await db_session.refresh(locker_box)
    assert locker_box.is_available is False


@pytest.mark.asyncio
async def test_initiate_return_invalid_status(client: AsyncClient, db_session: AsyncSession):
    """Return 400 when order status is not 'picked_up'."""
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

    locker = Locker(
        locker_code="WRO-003",
        street="Test St",
        city="Wroclaw",
        postal_code="50-003",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    order = Order(reader_id=user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/initiate-return",
        json={"locker_id": str(locker.id)},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "Cannot initiate return" in res.json()["detail"]


@pytest.mark.asyncio
async def test_initiate_return_no_available_boxes(client: AsyncClient, db_session: AsyncSession):
    """Return 400 when no boxes available in selected locker."""
    user = User(
        email="noboxes@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Boxes",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    locker = Locker(
        locker_code="WRO-004",
        street="Full St",
        city="Wroclaw",
        postal_code="50-004",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    # All boxes occupied
    locker_box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(locker_box)
    await db_session.commit()

    order = Order(reader_id=user.id, status=OrderStatus.PICKED_UP)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/initiate-return",
        json={"locker_id": str(locker.id)},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "No available boxes" in res.json()["detail"]
