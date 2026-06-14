"""Tests for POST /api/librarian/orders/{id}/accept_return endpoint."""

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Book,
    BookItem,
    Locker,
    LockerBox,
    LockerShipment,
    Order,
    OrderItem,
    User,
)
from models.enums import BookLocation, OrderStatus


@pytest.mark.asyncio
async def test_accept_return_success(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test successful acceptance of book return."""

    # Create book and item
    book = Book(isbn="9788379246199", title="Test Book", authors="Test Author")
    db_session.add(book)

    item = BookItem(
        isbn=book.isbn,
        is_available=False,
        current_location=BookLocation.LOCKER,
    )
    db_session.add(item)

    # Create locker and box
    locker = Locker(
        locker_code="WRO-001",
        street="Test Street",
        city="Wrocław",
        postal_code="50-000",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.flush()

    box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(box)
    await db_session.flush()

    # Create order with return in progress
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item)

    # Create order item
    order_item = OrderItem(
        order_id=order.id,
        book_item_id=item.id,
    )
    db_session.add(order_item)

    # Create return shipment
    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=box.id,
        mode="return",
        status="placed_in_locker",
        pickup_code="TEST1234",
    )
    db_session.add(shipment)
    await db_session.commit()

    # ✅ SZCZEGÓŁOWY DEBUG
    url = f"/api/librarian/orders/{order.id}/accept_return"
    print(f"\n{'=' * 80}")
    print(f"🔍 CALLING URL: {url}")
    print(f"🔍 Order ID: {order.id}")
    print(f"🔍 Order ID type: {type(order.id)}")
    print(f"🔍 Order status: {order.status}")
    print(f"🔍 Token present: {bool(librarian_token)}")
    print(f"{'=' * 80}\n")

    # Accept return
    response = await client.post(
        url,
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    # ✅ DEBUG RESPONSE
    print(f"\n{'=' * 80}")
    print(f"📤 Response status: {response.status_code}")
    print(f"📤 Response body: {response.json()}")
    print(f"📤 Response headers: {dict(response.headers)}")
    print(f"{'=' * 80}\n")

    assert response.status_code == 200
    assert "accepted" in response.json()["message"].lower()

    # Verify order status changed to RETURNED
    await db_session.refresh(order)
    assert order.status == OrderStatus.RETURNED

    # Verify shipment marked as completed
    await db_session.refresh(shipment)
    assert shipment.status == "completed"

    # Verify order item has returned_at timestamp
    await db_session.refresh(order_item)
    assert order_item.returned_at is not None

    # Verify book item is available and back in library
    await db_session.refresh(item)
    assert item.is_available is True
    assert item.current_location == BookLocation.LIBRARY


@pytest.mark.asyncio
async def test_accept_return_order_not_found(
    client: AsyncClient,
    librarian_token: str,
):
    """Test accepting return for non-existent order."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/api/librarian/orders/{fake_uuid}/accept_return",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_accept_return_wrong_order_status(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test accepting return for order not in return_in_progress status."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.PICKED_UP)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/accept_return",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 400
    assert "return_in_progress" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_accept_return_no_return_shipment(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test accepting return when return shipment doesn't exist."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/accept_return",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 404
    assert "shipment" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_accept_return_wrong_shipment_status(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test accepting return when shipment is not in placed_in_locker status."""
    # Create locker and box
    locker = Locker(
        locker_code="WRO-001",
        street="Test Street",
        city="Wrocław",
        postal_code="50-000",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.flush()

    box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(box)
    await db_session.flush()

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # Create return shipment with 'created' status (not placed yet)
    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=box.id,
        mode="return",
        status="created",  # Wrong status
        pickup_code="TEST1234",
    )
    db_session.add(shipment)
    await db_session.commit()

    response = await client.post(
        f"/api/librarian/orders/{order.id}/accept_return",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 400
    assert "placed_in_locker" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_accept_return_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_user: User,
):
    """Test accepting return without authentication."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(f"/api/librarian/orders/{order.id}/accept_return")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_accept_return_forbidden_for_reader(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_token: str,
    reader_user: User,
):
    """Test that readers cannot accept returns."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/accept_return",
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_accept_return_multiple_books(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test accepting return with multiple books."""
    # Create books and items
    book1 = Book(isbn="9788379246199", title="Book 1", authors="Author 1")
    book2 = Book(isbn="9788324086689", title="Book 2", authors="Author 2")
    db_session.add_all([book1, book2])

    item1 = BookItem(isbn=book1.isbn, is_available=False, current_location=BookLocation.LOCKER)
    item2 = BookItem(isbn=book2.isbn, is_available=False, current_location=BookLocation.LOCKER)
    db_session.add_all([item1, item2])

    # Create locker and box
    locker = Locker(
        locker_code="WRO-001",
        street="Test Street",
        city="Wrocław",
        postal_code="50-000",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    db_session.add(locker)
    await db_session.flush()

    box = LockerBox(locker_id=locker.id, number=1, is_available=False)
    db_session.add(box)
    await db_session.flush()

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.RETURN_IN_PROGRESS)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item1)
    await db_session.refresh(item2)

    # Create order items
    oi1 = OrderItem(order_id=order.id, book_item_id=item1.id)
    oi2 = OrderItem(order_id=order.id, book_item_id=item2.id)
    db_session.add_all([oi1, oi2])

    # Create return shipment
    shipment = LockerShipment(
        order_id=order.id,
        locker_box_id=box.id,
        mode="return",
        status="placed_in_locker",
        pickup_code="TEST1234",
    )
    db_session.add(shipment)
    await db_session.commit()

    # Accept return
    response = await client.post(
        f"/api/librarian/orders/{order.id}/accept_return",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200

    # Verify both items released
    await db_session.refresh(item1)
    await db_session.refresh(item2)

    assert item1.is_available is True
    assert item1.current_location == BookLocation.LIBRARY
    assert item2.is_available is True
    assert item2.current_location == BookLocation.LIBRARY

    # Verify both order items have returned_at
    await db_session.refresh(oi1)
    await db_session.refresh(oi2)

    assert oi1.returned_at is not None
    assert oi2.returned_at is not None
