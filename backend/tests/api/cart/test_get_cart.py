# === tests/api/cart/test_get_cart.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_get_cart_creates_empty_cart_if_none(client: AsyncClient, db_session: AsyncSession):
    """Should create an empty active cart if user doesn't have one."""
    user = User(
        email="reader@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Test",
        last_name="User",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    response = await client.get("/api/cart", headers={"Authorization": f"Bearer test-{user.id}"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(user.id)
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["id"] is not None

    cart = await db_session.get(Cart, data["id"])
    assert cart.status == CartStatus.ACTIVE


@pytest.mark.asyncio
async def test_get_cart_returns_existing_items(client: AsyncClient, db_session: AsyncSession):
    """Should return all items from user's active cart."""
    user = User(
        email="reader2@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Alice",
        last_name="Smith",
    )
    book = Book(
        isbn="9781111111111",
        title="Clean Code",
        authors="Robert C. Martin",
        publisher="Prentice Hall",
    )
    db_session.add_all([user, book])
    await db_session.flush()

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()

    item = CartItem(cart_id=cart.id, isbn=book.isbn, quantity=2)
    db_session.add(item)
    await db_session.commit()

    response = await client.get("/api/cart", headers={"Authorization": f"Bearer test-{user.id}"})
    assert response.status_code == 200

    data = response.json()
    assert data["user_id"] == str(user.id)
    assert len(data["items"]) == 1
    assert data["items"][0]["isbn"] == "9781111111111"
    assert data["items"][0]["quantity"] == 2
    assert data["total_items"] == 2


@pytest.mark.asyncio
async def test_get_cart_multiple_books_sum_quantities(
    client: AsyncClient, db_session: AsyncSession
):
    """Should correctly sum total_items across multiple cart items."""
    user = User(
        email="multi@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Multi",
        last_name="User",
    )
    books = [
        Book(isbn="9780000000001", title="Book A", authors="Author A"),
        Book(isbn="9780000000002", title="Book B", authors="Author B"),
    ]
    db_session.add_all([user, *books])
    await db_session.flush()

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()

    db_session.add_all(
        [
            CartItem(cart_id=cart.id, isbn=books[0].isbn, quantity=1),
            CartItem(cart_id=cart.id, isbn=books[1].isbn, quantity=3),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/cart", headers={"Authorization": f"Bearer test-{user.id}"})
    assert res.status_code == 200
    data = res.json()

    assert len(data["items"]) == 2
    assert data["total_items"] == 4


@pytest.mark.asyncio
async def test_get_cart_unauthenticated(client: AsyncClient):
    """Should return 401 when no auth header provided."""
    res = await client.get("/api/cart")
    assert res.status_code == 401
