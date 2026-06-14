"""Tests for POST /api/librarian/orders/{id}/assign-items endpoint."""

import pytest

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Order, OrderItem, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus


@pytest.mark.asyncio
async def test_assign_items_success(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test successful assignment of book items to order."""
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
    await db_session.refresh(item1)
    await db_session.refresh(item2)

    # Add requested item
    requested = OrderRequestedItem(
        order_id=order.id,
        isbn=book.isbn,
        quantity=2,
    )
    db_session.add(requested)
    await db_session.commit()

    # Assign items
    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={
            "items": [
                {
                    "isbn": book.isbn,
                    "book_item_ids": [str(item1.id), str(item2.id)],
                }
            ]
        },
    )

    assert response.status_code == 200
    assert "assigned" in response.json()["message"].lower()

    # Verify order status changed
    await db_session.refresh(order)
    assert order.status == OrderStatus.READY_FOR_PICKUP

    # Verify OrderItems created
    result = await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = result.scalars().all()
    assert len(order_items) == 2

    # Verify BookItems marked as unavailable and in locker
    await db_session.refresh(item1)
    await db_session.refresh(item2)

    assert item1.is_available is False
    assert item1.current_location == BookLocation.TRANSIT
    assert item2.is_available is False
    assert item2.current_location == BookLocation.TRANSIT


@pytest.mark.asyncio
async def test_assign_items_order_not_found(
    client: AsyncClient,
    librarian_token: str,
):
    """Test assigning items to non-existent order."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/api/librarian/orders/{fake_uuid}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={"items": []},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_assign_items_wrong_status(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test assigning items to order that is not NEW."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={"items": []},
    )

    assert response.status_code == 400
    assert "new" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_book_item_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test assigning non-existent book item."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    fake_item_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={
            "items": [
                {
                    "isbn": "9788379246199",
                    "book_item_ids": [fake_item_uuid],
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_unavailable_book_item(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test assigning book item that is not available."""

    # ✅ DODAJ: Create book first
    book = Book(
        isbn="9788379246199",
        title="Test Book",
        authors="Test Author",
    )
    db_session.add(book)
    await db_session.flush()

    # Create unavailable book item
    item = BookItem(
        isbn="9788379246199",
        is_available=False,
        current_location=BookLocation.TRANSIT,
    )
    db_session.add(item)

    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={
            "items": [
                {
                    "isbn": "9788379246199",
                    "book_item_ids": [str(item.id)],
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "not available" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_user: User,
):
    """Test assigning items without authentication."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        json={"items": []},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_assign_items_forbidden_for_reader(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_token: str,
    reader_user: User,
):
    """Test that readers cannot assign items."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {reader_token}"},
        json={"items": []},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_assign_items_multiple_books(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test assigning items for multiple different books."""
    # Create two books
    book1 = Book(isbn="9788379246199", title="Book 1", authors="Author 1")
    book2 = Book(isbn="9788324086689", title="Book 2", authors="Author 2")
    db_session.add_all([book1, book2])

    # Create items for each book
    item1 = BookItem(isbn=book1.isbn, is_available=True, current_location=BookLocation.LIBRARY)
    item2 = BookItem(isbn=book2.isbn, is_available=True, current_location=BookLocation.LIBRARY)
    db_session.add_all([item1, item2])

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item1)
    await db_session.refresh(item2)

    # Assign items
    response = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer {librarian_token}"},
        json={
            "items": [
                {"isbn": book1.isbn, "book_item_ids": [str(item1.id)]},
                {"isbn": book2.isbn, "book_item_ids": [str(item2.id)]},
            ]
        },
    )

    assert response.status_code == 200

    # Verify both items assigned
    result = await db_session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
    order_items = result.scalars().all()
    assert len(order_items) == 2
