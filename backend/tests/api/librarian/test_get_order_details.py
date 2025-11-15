# === tests/api/librarian/test_get_order_details.py ===

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
async def test_get_order_details_returns_correct_structure(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return full order details including requested books + available copies."""

    # --- Arrange: librarian ---
    librarian = User(
        email="lib@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib",
        last_name="One",
    )

    # --- Readers, books ---
    reader = User(
        email="reader@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Reader",
        last_name="One",
    )

    book = Book(
        isbn="111-222-333",
        title="Clean Code",
        authors="Robert Martin",
    )

    # Save users + book
    db_session.add_all([librarian, reader, book])
    await db_session.commit()
    await db_session.refresh(librarian)
    await db_session.refresh(reader)

    # --- Order + requested items ---
    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.flush()  # generate order.id now

    requested = OrderRequestedItem(order_id=order.id, isbn=book.isbn, quantity=2)

    # Available copies
    bi1 = BookItem(isbn=book.isbn, is_available=True, current_location=BookLocation.LIBRARY)
    bi2 = BookItem(isbn=book.isbn, is_available=True, current_location=BookLocation.LIBRARY)

    db_session.add_all([requested, bi1, bi2])
    await db_session.commit()

    # --- Act ---
    res = await client.get(
        f"/api/librarian/orders/{order.id}",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
    )

    # --- Assert ---
    assert res.status_code == 200
    data = res.json()

    assert data["order_id"] == str(order.id)
    assert data["status"] == order.status.value
    assert data["reader_email"] == reader.email

    # Books requested
    assert len(data["books"]) == 1
    assert data["books"][0]["isbn"] == book.isbn
    assert data["books"][0]["title"] == "Clean Code"
    assert data["books"][0]["quantity"] == 2

    # Available items
    assert book.isbn in data["available_items"]
    assert len(data["available_items"][book.isbn]) == 2


@pytest.mark.asyncio
async def test_get_order_details_not_found(client: AsyncClient, db_session: AsyncSession):
    """Should return 404 for a non-existing order."""

    # Need a valid librarian so authorization passes
    librarian = User(
        email="lib2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib2",
        last_name="Test",
    )
    db_session.add(librarian)
    await db_session.commit()
    await db_session.refresh(librarian)

    non_existing_id = "99999999-9999-9999-9999-999999999999"

    res = await client.get(
        f"/api/librarian/orders/{non_existing_id}",
        headers={"Authorization": f"Bearer test-{librarian.id}"},
    )

    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_order_details_forbidden_for_reader(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return 403 when non-librarian tries to access."""

    # Create a normal reader
    reader = User(
        email="user@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Normal",
        last_name="User",
    )
    db_session.add(reader)
    await db_session.commit()
    await db_session.refresh(reader)

    # Create an order assigned to them
    order = Order(reader_id=reader.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    # --- Act: reader tries to access librarian endpoint ---
    res = await client.get(
        f"/api/librarian/orders/{order.id}",
        headers={"Authorization": f"Bearer test-{reader.id}"},
    )

    # --- Assert ---
    assert res.status_code == 403
    assert "librarian" in res.json()["detail"].lower()
