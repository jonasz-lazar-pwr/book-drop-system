# === tests/api/cart/test_clear_cart.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_clear_cart_removes_all_items(client: AsyncClient, db_session: AsyncSession):
    """Should remove all items from the user's active cart."""
    user = User(
        email="clear@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Clear",
        last_name="Cart",
    )
    books = [
        Book(isbn="9781111111115", title="Book A", authors="Author A"),
        Book(isbn="9782222222225", title="Book B", authors="Author B"),
    ]
    db_session.add_all([user, *books])
    await db_session.commit()
    await db_session.refresh(user)

    # Create active cart with two items
    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()
    db_session.add_all(
        [
            CartItem(cart_id=cart.id, isbn=books[0].isbn, quantity=1),
            CartItem(cart_id=cart.id, isbn=books[1].isbn, quantity=2),
        ]
    )
    await db_session.commit()

    res = await client.delete(
        "/api/cart/clear",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["items"] == []
    assert data["total_items"] == 0

    # Verify DB state: no CartItem records left
    result = await db_session.execute(select(CartItem).where(CartItem.cart_id == cart.id))
    remaining_items = result.scalars().all()
    assert len(remaining_items) == 0


@pytest.mark.asyncio
async def test_clear_cart_when_already_empty(client: AsyncClient, db_session: AsyncSession):
    """Should return empty cart when clearing an already empty cart."""
    user = User(
        email="emptyclear@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Empty",
        last_name="Clear",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.commit()

    res = await client.delete(
        "/api/cart/clear",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total_items"] == 0


@pytest.mark.asyncio
async def test_clear_cart_creates_new_cart_if_none(client: AsyncClient, db_session: AsyncSession):
    """Should create a new active cart if user has none yet."""
    user = User(
        email="nocartclear@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Cart",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Act
    res = await client.delete(
        "/api/cart/clear",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["user_id"] == str(user.id)
    assert data["items"] == []
    assert data["total_items"] == 0
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_clear_cart_unauthenticated(client: AsyncClient):
    """Should return 401 when no auth header is provided."""
    res = await client.delete("/api/cart/clear")
    assert res.status_code == 401
