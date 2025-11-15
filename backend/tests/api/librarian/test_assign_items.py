# === tests/api/librarian/test_assign_items.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Book,
    BookItem,
    Order,
    OrderRequestedItem,
    User,
)
from models.enums import (
    BookLocation,
    OrderStatus,
    UserRole,
)


@pytest.mark.asyncio
async def test_assign_items_success(client: AsyncClient, db_session: AsyncSession):
    """Should assign book items and update DB state when librarian calls endpoint."""

    # --- Librarian ---
    librarian = User(
        email="lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib",
        last_name="A",
    )

    # --- Reader + order ---
    reader = User(
        email="reader@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Reader",
        last_name="A",
    )

    book = Book(isbn="AAA-BBB-CCC", title="Clean Code", authors="Robert Martin")

    db_session.add_all([librarian, reader, book])
    await db_session.commit()
    await db_session.refresh(librarian)
    await db_session.refresh(reader)

    # Order
    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.flush()

    # Requested 2 sztuki
    req = OrderRequestedItem(order_id=order.id, isbn=book.isbn, quantity=2)

    # Available copies
    bi1 = BookItem(isbn=book.isbn, is_available=True, current_location=BookLocation.LIBRARY)
    bi2 = BookItem(isbn=book.isbn, is_available=True, current_location=BookLocation.LIBRARY)

    db_session.add_all([req, bi1, bi2])
    await db_session.commit()

    body = {
        "items": [
            {
                "isbn": book.isbn,
                "book_item_ids": [str(bi1.id), str(bi2.id)],
            }
        ]
    }

    # --- Act ---
    res = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
        json=body,
    )

    # --- Assert ---
    assert res.status_code == 200
    assert "assigned" in res.json()["message"].lower()

    # Verify DB state
    await db_session.refresh(order)
    assert order.status == OrderStatus.PREPARED

    await db_session.refresh(bi1)
    await db_session.refresh(bi2)
    assert bi1.is_available is False
    assert bi2.is_available is False
    assert bi1.current_location == BookLocation.TRANSIT
    assert bi2.current_location == BookLocation.TRANSIT


@pytest.mark.asyncio
async def test_assign_items_order_not_found(client: AsyncClient, db_session: AsyncSession):
    """Should return 404 if order does not exist."""

    librarian = User(
        email="lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="X",
        last_name="Y",
    )
    db_session.add(librarian)
    await db_session.commit()
    await db_session.refresh(librarian)

    res = await client.post(
        "/api/librarian/orders/99999999-9999-9999-9999-999999999999/assign-items",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
        json={"items": []},
    )

    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_fails_when_bookitem_invalid(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return 400 when book_item_ids contains non-existing BookItem IDs."""

    librarian = User(
        email="lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="X",
        last_name="Y",
    )
    reader = User(
        email="r@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="R",
        last_name="A",
    )
    book = Book(isbn="ABC", title="Book", authors="A")

    db_session.add_all([librarian, reader, book])
    await db_session.commit()
    await db_session.refresh(librarian)
    await db_session.refresh(reader)

    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    body = {"items": [{"isbn": "ABC", "book_item_ids": ["00000000-0000-0000-0000-000000000000"]}]}

    res = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
        json=body,
    )

    assert res.status_code == 400
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_fails_when_bookitem_unavailable(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return 400 if a BookItem is not available."""

    librarian = User(
        email="lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="L",
        last_name="A",
    )
    reader = User(
        email="r@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="R",
        last_name="A",
    )
    book = Book(isbn="ABC", title="T", authors="A")

    db_session.add_all([librarian, reader, book])
    await db_session.commit()
    await db_session.refresh(librarian)
    await db_session.refresh(reader)

    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.flush()

    req = OrderRequestedItem(order_id=order.id, isbn=book.isbn, quantity=1)

    bi = BookItem(isbn=book.isbn, is_available=False, current_location=BookLocation.LIBRARY)

    db_session.add_all([order, req, bi])
    await db_session.commit()

    body = {"items": [{"isbn": book.isbn, "book_item_ids": [str(bi.id)]}]}

    res = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
        json=body,
    )

    assert res.status_code == 400
    assert "not available" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_forbidden_for_reader(client: AsyncClient, db_session: AsyncSession):
    """Should return 403 when user is not a librarian."""

    # Create reader
    reader = User(
        email="reader@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="R",
        last_name="A",
    )

    # Create an actual order belonging to the same reader
    db_session.add(reader)
    await db_session.commit()
    await db_session.refresh(reader)

    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    res = await client.post(
        f"/api/librarian/orders/{order.id}/assign-items",
        headers={"Authorization": f"Bearer test-{reader.id}"},
        json={"items": []},
    )

    assert res.status_code == 403
    assert "librarian" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_assign_items_unauthorized(client: AsyncClient):
    """Should return 401 without authentication."""
    res = await client.post("/api/librarian/orders/123/assign-items", json={"items": []})
    assert res.status_code == 401
