# === tests/api/cart/test_update_quantity.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_update_quantity_success(client: AsyncClient, db_session: AsyncSession):
    """Should update quantity successfully for an existing cart item."""
    user = User(
        email="update@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Update",
        last_name="User",
    )
    book = Book(isbn="9781111111112", title="Clean Architecture", authors="Robert Martin")
    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, isbn=book.isbn, quantity=1))
    await db_session.commit()

    payload = {"quantity": 3}
    res = await client.patch(
        f"/api/cart/items/{book.isbn}",
        json=payload,
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3
    assert data["total_items"] == 3

    # Verify DB updated
    item = await db_session.scalar(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.isbn == book.isbn)
    )
    assert item.quantity == 3


@pytest.mark.asyncio
async def test_update_quantity_invalid_value(client: AsyncClient, db_session: AsyncSession):
    """Should return 400 when quantity < 1."""
    user = User(
        email="invalid@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Invalid",
        last_name="Quantity",
    )
    book = Book(isbn="9782222222222", title="Domain-Driven Design", authors="Eric Evans")
    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()
    db_session.add(CartItem(cart_id=cart.id, isbn=book.isbn, quantity=2))
    await db_session.commit()

    res = await client.patch(
        f"/api/cart/items/{book.isbn}",
        json={"quantity": 0},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 400
    assert res.json()["detail"] == "Quantity must be positive."


@pytest.mark.asyncio
async def test_update_quantity_item_not_found(client: AsyncClient, db_session: AsyncSession):
    """Should return 404 if the item does not exist in the cart."""
    user = User(
        email="nofound@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Item",
    )
    book = Book(isbn="9783333333333", title="Refactoring UI", authors="Adam Wathan")
    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    # User has an empty active cart
    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.commit()

    res = await client.patch(
        f"/api/cart/items/{book.isbn}",
        json={"quantity": 2},
        headers={"Authorization": f"Bearer test-{user.id}"},
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Item not found."


@pytest.mark.asyncio
async def test_update_quantity_unauthenticated(client: AsyncClient):
    """Should return 401 when no auth header is provided."""
    res = await client.patch(
        "/api/cart/items/9781111111111",
        json={"quantity": 2},
    )
    assert res.status_code == 401
