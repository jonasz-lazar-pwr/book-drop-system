"""Tests for GET /api/librarian/orders/{id}/summary endpoint."""

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Order, OrderItem, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus


@pytest.mark.asyncio
async def test_get_order_summary_success(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test successful retrieval of order summary."""
    # Create book
    book = Book(
        isbn="9788379246199",
        title="Test Book",
        authors="Test Author",
        publisher="Test Publisher",
        published_date="2020",
    )
    db_session.add(book)

    # Create book item
    item = BookItem(
        isbn=book.isbn,
        is_available=False,
        current_location=BookLocation.TRANSIT,
    )
    db_session.add(item)

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item)

    # Add requested item
    requested = OrderRequestedItem(
        order_id=order.id,
        isbn=book.isbn,
        quantity=1,
    )
    db_session.add(requested)

    # Add order item (assigned)
    order_item = OrderItem(
        order_id=order.id,
        book_item_id=item.id,
    )
    db_session.add(order_item)
    await db_session.commit()

    # Get summary
    response = await client.get(
        f"/api/librarian/orders/{order.id}/summary",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify structure
    assert data["order_id"] == str(order.id)
    assert data["status"] == OrderStatus.PREPARED

    # Verify reader info
    assert data["reader"]["first_name"] == reader_user.first_name
    assert data["reader"]["last_name"] == reader_user.last_name
    assert data["reader"]["email"] == reader_user.email

    # Verify books
    assert len(data["books"]) == 1
    book_data = data["books"][0]
    assert book_data["isbn"] == book.isbn
    assert book_data["title"] == book.title
    assert book_data["authors"] == book.authors
    assert book_data["publisher"] == book.publisher
    assert book_data["published_date"] == book.published_date
    assert book_data["quantity"] == 1
    assert str(item.id) in book_data["assigned_items"]


@pytest.mark.asyncio
async def test_get_order_summary_not_found(
    client: AsyncClient,
    librarian_token: str,
):
    """Test getting summary for non-existent order."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"

    response = await client.get(
        f"/api/librarian/orders/{fake_uuid}/summary",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_order_summary_new_order(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test getting summary for NEW order (should fail)."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(
        f"/api/librarian/orders/{order.id}/summary",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 400
    assert "not prepared" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_order_summary_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_user: User,
):
    """Test getting summary without authentication."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(f"/api/librarian/orders/{order.id}/summary")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_order_summary_forbidden_for_reader(
    client: AsyncClient,
    db_session: AsyncSession,
    reader_token: str,
    reader_user: User,
):
    """Test that readers cannot access summary endpoint."""
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    response = await client.get(
        f"/api/librarian/orders/{order.id}/summary",
        headers={"Authorization": f"Bearer {reader_token}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_order_summary_multiple_books(
    client: AsyncClient,
    db_session: AsyncSession,
    librarian_token: str,
    reader_user: User,
):
    """Test summary with multiple books."""
    # Create books
    book1 = Book(isbn="9788379246199", title="Book 1", authors="Author 1")
    book2 = Book(isbn="9788324086689", title="Book 2", authors="Author 2")
    db_session.add_all([book1, book2])

    # Create items
    item1 = BookItem(isbn=book1.isbn, is_available=False)
    item2a = BookItem(isbn=book2.isbn, is_available=False)
    item2b = BookItem(isbn=book2.isbn, is_available=False)
    db_session.add_all([item1, item2a, item2b])

    # Create order
    order = Order(reader_id=reader_user.id, status=OrderStatus.PREPARED)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)
    await db_session.refresh(item1)
    await db_session.refresh(item2a)
    await db_session.refresh(item2b)

    # Add requested items
    req1 = OrderRequestedItem(order_id=order.id, isbn=book1.isbn, quantity=1)
    req2 = OrderRequestedItem(order_id=order.id, isbn=book2.isbn, quantity=2)
    db_session.add_all([req1, req2])

    # Add order items
    oi1 = OrderItem(order_id=order.id, book_item_id=item1.id)
    oi2a = OrderItem(order_id=order.id, book_item_id=item2a.id)
    oi2b = OrderItem(order_id=order.id, book_item_id=item2b.id)
    db_session.add_all([oi1, oi2a, oi2b])
    await db_session.commit()

    # Get summary
    response = await client.get(
        f"/api/librarian/orders/{order.id}/summary",
        headers={"Authorization": f"Bearer {librarian_token}"},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify books
    assert len(data["books"]) == 2

    # Find book2 (should have 2 assigned items)
    book2_data = next(b for b in data["books"] if b["isbn"] == book2.isbn)
    assert book2_data["quantity"] == 2
    assert len(book2_data["assigned_items"]) == 2
