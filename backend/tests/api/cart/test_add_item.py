# === tests/api/cart/test_add_item.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_add_item_creates_cart_and_adds_book(client: AsyncClient, db_session: AsyncSession):
    """Create new active cart and add book when none exists."""
    user = User(
        email="user1@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Add",
        last_name="User",
    )
    book = Book(
        isbn="9789999999999",
        title="Refactoring",
        authors="Martin Fowler",
        publisher="Addison-Wesley",
    )
    db_session.add_all([user, book])
    await db_session.commit()

    book_item = BookItem(isbn=book.isbn, is_available=True)
    db_session.add(book_item)
    await db_session.commit()
    await db_session.refresh(user)

    res = await client.post(
        "/api/cart/items",
        json={"isbn": book.isbn},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == str(user.id)
    assert len(data["items"]) == 1
    assert data["items"][0]["isbn"] == book.isbn
    assert data["items"][0]["quantity"] == 1
    assert data["total_items"] == 1

    cart = await db_session.scalar(select(Cart).where(Cart.user_id == user.id))
    assert cart is not None
    assert cart.status == CartStatus.ACTIVE


@pytest.mark.asyncio
async def test_add_item_increments_quantity_if_already_in_cart(
    client: AsyncClient, db_session: AsyncSession
):
    """Increment quantity when the same book is added again."""
    user = User(
        email="user2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Repeat",
        last_name="User",
    )
    book = Book(isbn="9788888888888", title="DDD", authors="Eric Evans")
    db_session.add_all([user, book])
    await db_session.commit()

    db_session.add_all(
        [
            BookItem(isbn=book.isbn, is_available=True),
            BookItem(isbn=book.isbn, is_available=True),
        ]
    )
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()

    db_session.add(CartItem(cart_id=cart.id, isbn=book.isbn, quantity=1))
    await db_session.commit()

    res = await client.post(
        "/api/cart/items",
        json={"isbn": book.isbn},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["items"][0]["quantity"] == 2
    assert data["total_items"] == 2


@pytest.mark.asyncio
async def test_add_item_returns_404_for_nonexistent_book(
    client: AsyncClient, db_session: AsyncSession
):
    """Return 404 when trying to add non-existent book."""
    user = User(
        email="no_book@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Book",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    res = await client.post(
        "/api/cart/items",
        json={"isbn": "0000000000000"},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 404
    data = res.json()
    assert "Book not found" in data["detail"]


@pytest.mark.asyncio
async def test_add_item_unauthenticated(client: AsyncClient):
    """Return 401 when no Authorization header provided."""
    res = await client.post("/api/cart/items", json={"isbn": "9789999999999"})
    assert res.status_code == 401
