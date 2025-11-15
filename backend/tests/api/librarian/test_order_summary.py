# === tests/api/librarian/test_order_summary.py

import pytest
import pytest_asyncio

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Order, OrderItem, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus, UserRole


@pytest_asyncio.fixture
async def librarian_user(db_session: AsyncSession):
    user = User(
        email="lib@test.pl",
        password="hashed",  # noqa: S106
        role=UserRole.LIBRARIAN,
        first_name="Lib",
        last_name="Rarian",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def reader_user(db_session: AsyncSession):
    user = User(
        email="reader@test.pl",
        password="hashed",  # noqa: S106
        role=UserRole.READER,
        first_name="Adam",
        last_name="Nowak",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def sample_book(db_session: AsyncSession):
    book = Book(
        isbn="9781234567890",
        title="Algorytmy",
        authors="Sedgewick",
        publisher="Helion",
        published_date="2018",
    )
    db_session.add(book)
    await db_session.commit()
    await db_session.refresh(book)
    return book


@pytest_asyncio.fixture
async def prepared_order(db_session: AsyncSession, reader_user, sample_book):
    order = Order(
        reader_id=reader_user.id,
        status=OrderStatus.PREPARED,
    )
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    req = OrderRequestedItem(order_id=order.id, isbn=sample_book.isbn, quantity=2)
    db_session.add(req)
    await db_session.commit()

    bi1 = BookItem(isbn=sample_book.isbn, is_available=False, current_location=BookLocation.TRANSIT)
    bi2 = BookItem(isbn=sample_book.isbn, is_available=False, current_location=BookLocation.TRANSIT)
    db_session.add_all([bi1, bi2])
    await db_session.commit()
    await db_session.refresh(bi1)
    await db_session.refresh(bi2)

    oi1 = OrderItem(order_id=order.id, book_item_id=bi1.id)
    oi2 = OrderItem(order_id=order.id, book_item_id=bi2.id)
    db_session.add_all([oi1, oi2])
    await db_session.commit()

    return order


@pytest.mark.asyncio
async def test_summary_requires_auth(client: AsyncClient):
    resp = await client.get("/api/librarian/orders/123/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_summary_requires_librarian_role(client: AsyncClient, reader_user):
    resp = await client.get(
        "/api/librarian/orders/123/summary",
        headers={"Authorization": f"Bearer test-{reader_user.id}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_summary_not_found(client: AsyncClient, librarian_user):
    resp = await client.get(
        "/api/librarian/orders/00000000-0000-0000-0000-000000000001/summary",
        headers={"Authorization": f"Bearer test-{librarian_user.id}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summary_rejects_new_orders(
    db_session: AsyncSession, client: AsyncClient, librarian_user, reader_user
):
    order = Order(reader_id=reader_user.id, status=OrderStatus.NEW)
    db_session.add(order)
    await db_session.commit()
    await db_session.refresh(order)

    resp = await client.get(
        f"/api/librarian/orders/{order.id}/summary",
        headers={"Authorization": f"Bearer test-{librarian_user.id}"},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Order is not prepared yet — no summary available."


@pytest.mark.asyncio
async def test_summary_success(
    client: AsyncClient, db_session: AsyncSession, librarian_user, prepared_order
):
    resp = await client.get(
        f"/api/librarian/orders/{prepared_order.id}/summary",
        headers={"Authorization": f"Bearer test-{librarian_user.id}"},
    )

    assert resp.status_code == 200
    data = resp.json()

    assert data["order_id"] == str(prepared_order.id)
    assert data["status"] == "prepared"
    assert "created_at" in data

    reader = data["reader"]
    assert reader["first_name"] == "Adam"
    assert reader["last_name"] == "Nowak"
    assert reader["email"] == "reader@test.pl"

    book = data["books"][0]
    assert book["isbn"] == "9781234567890"
    assert book["title"] == "Algorytmy"
    assert book["authors"] == "Sedgewick"
    assert book["publisher"] == "Helion"
    assert book["published_date"] == "2018"
    assert book["quantity"] == 2
    assert len(book["assigned_items"]) == 2

    for bi_id in book["assigned_items"]:
        q = await db_session.execute(select(BookItem).where(BookItem.id == bi_id))
        assert q.scalar() is not None
