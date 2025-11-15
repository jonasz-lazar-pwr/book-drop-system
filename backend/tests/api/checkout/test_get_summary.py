# === tests/api/checkout/test_get_summary.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, Cart, CartItem, User
from models.enums import CartStatus, UserRole


@pytest.mark.asyncio
async def test_get_summary_returns_active_cart(client: AsyncClient, db_session: AsyncSession):
    """Should return checkout summary for active cart."""
    # Arrange
    user = User(
        email="checkout@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Checkout",
        last_name="User",
    )
    book = Book(isbn="9781234567890", title="Domain-Driven Design", authors="Eric Evans")

    db_session.add_all([user, book])
    await db_session.commit()
    await db_session.refresh(user)

    cart = Cart(user_id=user.id, status=CartStatus.ACTIVE)
    db_session.add(cart)
    await db_session.flush()

    cart_item = CartItem(cart_id=cart.id, isbn=book.isbn, quantity=2)
    db_session.add(cart_item)
    await db_session.commit()

    # Act
    res = await client.get(
        "/api/checkout/summary",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    # Assert
    assert res.status_code == 200
    data = res.json()

    assert data["user_id"] == str(user.id)
    assert data["email"] == user.email
    assert data["total_items"] == 2
    assert data["distinct_titles"] == 1

    assert data["books"][0]["isbn"] == book.isbn
    assert data["books"][0]["title"] == "Domain-Driven Design"
    assert data["books"][0]["quantity"] == 2


@pytest.mark.asyncio
async def test_get_summary_fails_if_no_active_cart(client: AsyncClient, db_session: AsyncSession):
    """Should return 400 if user has no active cart."""
    user = User(
        email="nosummary@example.com",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="No",
        last_name="Summary",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Act
    res = await client.get(
        "/api/checkout/summary",
        headers={"Authorization": f"Bearer test-{user.id}"},
    )

    # Assert
    assert res.status_code == 400
    assert "active" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_summary_unauthorized(client: AsyncClient):
    """Should return 401 if user is not authenticated."""
    res = await client.get("/api/checkout/summary")
    assert res.status_code == 401
