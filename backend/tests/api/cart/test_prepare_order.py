# === tests/api/cart/test_prepare_order.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_prepare_order_locks_cart_and_returns_summary(
    client: AsyncClient, db_session: AsyncSession
):
    """Should validate cart, lock it (set SUBMITTED) and return summary."""
    user = User(
        email="prepare@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Prepare",
        last_name="Order",
    )
    book = Book(isbn="9780000000001", title="Clean Architecture", authors="Robert Martin")
    book_item = BookItem(isbn=book.isbn, is_available=True)
    db_session.add_all([user, book, book_item])
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()

    db_session.add(CartItem(cart_id=cart.id, isbn=book.isbn, quantity=1))
    await db_session.commit()

    # Act
    res = await client.post(
        "/api/cart/prepare-order",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    # Assert
    assert res.status_code == 200
    data = res.json()
    assert data["message"].startswith("Cart validated successfully")
    assert data["user_id"] == str(user.id)
    assert data["total_items"] == 1
    assert data["distinct_titles"] == 1


@pytest.mark.asyncio
async def test_prepare_order_fails_if_cart_empty(client: AsyncClient, db_session: AsyncSession):
    """Should return 400 if user has no items in cart."""
    user = User(
        email="empty@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Empty",
        last_name="Cart",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.commit()

    res = await client.post(
        "/api/cart/prepare-order",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_prepare_order_fails_if_already_submitted(
    client: AsyncClient, db_session: AsyncSession
):
    """Should return 400 if the cart is already submitted."""
    user = User(
        email="already@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Already",
        last_name="Submitted",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.SUBMITTED)
    db_session.add(cart)
    await db_session.commit()

    res = await client.post(
        "/api/cart/prepare-order",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 400
    assert "active cart" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_prepare_order_unauthenticated(client: AsyncClient):
    """Should return 401 when user not logged in."""
    res = await client.post("/api/cart/prepare-order")
    assert res.status_code == 401
