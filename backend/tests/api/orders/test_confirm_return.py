# tests/api/orders/test_confirm_return.py

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Locker, LockerBox, LockerShipment, Order, User
from models.enums import OrderStatus, ShipmentStatus, UserRole


@pytest.mark.asyncio
async def test_confirm_return_success(client: AsyncClient, db_session: AsyncSession):
    """Successfully confirm return placement in locker."""
    user = User(
        email="confirmreturn@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Confirm",
        last_name="Return",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    locker = Locker(
        locker_code="WRO-005",
        street="Confirm St",
        city="Wroclaw",
        postal_code="50-005",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.commit()

    locker_box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(locker_box)
    await db_session.commit()

    order = Order(reader_id=user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()

    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=locker_box.id,
        mode="return",
        status="created",
        pickup_code="RET12345",
    )
    db_session.add(shipment)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/confirm-return",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert "Return confirmed" in data["message"]

    # Verify database changes
    await db_session.refresh(shipment)
    assert shipment.status == ShipmentStatus.PLACED_IN_LOCKER
    assert shipment.placed_at is not None


@pytest.mark.asyncio
async def test_confirm_return_invalid_status(client: AsyncClient, db_session: AsyncSession):
    """Return 400 when order status is not 'return_in_progress'."""
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

    order = Order(reader_id=user.id, status=OrderStatus.PICKED_UP)
    db_session.add(order)
    await db_session.commit()

    res = await client.post(
        f"/api/orders/{order.id}/confirm-return",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "Cannot confirm return" in res.json()["detail"]
