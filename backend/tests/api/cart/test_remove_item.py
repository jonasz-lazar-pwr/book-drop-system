# === tests/api/cart/test_remove_item.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_remove_item_success(client: AsyncClient, db_session: AsyncSession):
    """Should remove an existing book from the user's cart."""
    user = User(
        email="remove1@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Remove",
        last_name="User",
    )
    book = Book(isbn="9784444444444", title="Design Patterns", authors="GoF")
    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    # Create active cart with one book
    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, isbn=book.isbn, quantity=2))
    await db_session.commit()

    # Act
    res = await client.delete(
        f"/api/cart/items/{book.isbn}",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    # Assert
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []  # no books left
    assert data["total_items"] == 0

    # Verify DB change
    item = await db_session.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.isbn == book.isbn)
    )
    assert item is None


@pytest.mark.asyncio
async def test_remove_item_not_in_cart(client: AsyncClient, db_session: AsyncSession):
    """Should return 404 if the book is not in the user's cart."""
    user = User(
        email="remove2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Missing",
        last_name="Book",
    )
    book_existing = Book(isbn="9785555555555", title="Algorithms", authors="Sedgewick")
    book_missing = Book(isbn="9786666666666", title="AI Revolution", authors="Smith")
    db_session.add_all([user, book_existing, book_missing])
    await db_session.commit()
    await db_session.refresh(user)

    # Cart contains only the first book
    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, isbn=book_existing.isbn, quantity=1))
    await db_session.commit()

    res = await client.delete(
        f"/api/cart/items/{book_missing.isbn}",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 404
    assert res.json()["detail"] == "Item not found."


@pytest.mark.asyncio
async def test_remove_item_from_empty_cart(client: AsyncClient, db_session: AsyncSession):
    """Should return 404 when trying to remove from an empty active cart."""
    user = User(
        email="emptycart@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Empty",
        last_name="Cart",
    )
    book = Book(isbn="9787777777777", title="The Pragmatic Programmer", authors="Hunt & Thomas")
    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    # Empty active cart
    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.commit()

    res = await client.delete(
        f"/api/cart/items/{book.isbn}",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Item not found."


@pytest.mark.asyncio
async def test_remove_item_unauthenticated(client: AsyncClient):
    """Should return 401 when no auth header is provided."""
    res = await client.delete("/api/cart/items/9784444444444")
    assert res.status_code == 401
