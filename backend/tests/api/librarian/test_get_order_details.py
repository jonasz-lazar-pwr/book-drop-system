"""Tests for GET /api/librarian/orders/{id} endpoint."""

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Order, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus


@pytest.mark.asyncio
async def test_get_order_details_success(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test successful retrieval of order details."""
    # Create book
    book = Book(
        isbn="9788379246199",
        title="Test Book",
        authors="Test Author",
        publisher="Test Publisher",
        published_date="2020",
    )
    db_session.add(book)

    # Create available book items
    item1 = BookItem(
        isbn=book.isbn,
        is_available=True,
        current_location=BookLocation.LIBRARY,
    )
    item2 = BookItem(
        isbn=book.isbn,
        is_available=True,
        current_location=BookLocation.LIBRARY,
    )
    db_session.add_all([item1, item2])

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # Add requested item
    requested = OrderRequestedItem(
        order_id=order.id,
        isbn=book.isbn,
        quantity=2,
    )
    db_session.add(requested)
    await db_session.commit()

    # Get order details
    response = await client.get(
        f"/api/librarian/orders/{order.id}",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert data["order_id"] == str(order.id)
    assert data["status"] == OrderStatus.NEW
    assert data["reader_email"] == reader_user.email
    assert data["reader_first_name"] == reader_user.first_name
    assert data["reader_last_name"] == reader_user.last_name

    # Verify books
    assert len(data["books"]) == 1
    assert data["books"][0]["isbn"] == book.isbn
    assert data["books"][0]["title"] == book.title
    assert data["books"][0]["quantity"] == 2

    # Verify available items
    assert book.isbn in data["available_items"]
    assert len(data["available_items"][book.isbn]) == 2

    first_item = data["available_items"][book.isbn][0]
    assert "id" in first_item
    assert first_item["location"] == BookLocation.LIBRARY
    assert first_item["is_available"] is True


@pytest.mark.asyncio
async def test_get_order_details_not_found(
    client: AsyncClient,
    librarian_token: str,
):
    """Test getting details for non-existent order."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.get(
        f"/api/librarian/orders/{fake_uuid}",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_order_details_invalid_uuid(
    client: AsyncClient,
    librarian_token: str,
):
    """Test getting details with invalid UUID format."""
    response = await client.get(
        "/api/librarian/orders/invalid-uuid",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_get_order_details_wrong_status(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test getting details for order that is not NEW."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(
        f"/api/librarian/orders/{order.id}",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 400
    assert "new" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_order_details_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_user: User,
):
    """Test getting order details without authentication."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(f"/api/librarian/orders/{order.id}")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_order_details_forbidden_for_reader(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_token: str,
    reader_user: User,
):
    """Test that readers cannot access order details endpoint."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(
        f"/api/librarian/orders/{order.id}",
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403
