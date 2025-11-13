# === tests/api/catalog/test_list_books.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem


@pytest.mark.asyncio
async def test_list_books_basic(client: AsyncClient, db_session: AsyncSession):
    """Should return a paginated list containing available books."""
    book = Book(
        isbn="9780000000001",
        title="Clean Code",
        authors="Robert C. Martin",
        publisher="Prentice Hall",
        published_date="2008-08-01",
    )
    db_session.add(book)
    db_session.add(BookItem(isbn=book.isbn, is_available=True, current_location="library"))
    await db_session.commit()

    response = await client.get("/api/catalog/books")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] == 1
    assert data["items"][0]["isbn"] == "9780000000001"
    assert data["items"][0]["available_count"] == 1


@pytest.mark.asyncio
async def test_list_books_with_filters(client: AsyncClient, db_session: AsyncSession):
    """Should correctly filter and sort books by search and publisher."""
    db_session.add_all(
        [
            Book(
                isbn="9780000000002",
                title="Domain-Driven Design",
                authors="Eric Evans",
                publisher="Addison-Wesley",
                published_date="2003-08-30",
            ),
            Book(
                isbn="9780000000003",
                title="Clean Architecture",
                authors="Robert C. Martin",
                publisher="Prentice Hall",
                published_date="2017-09-20",
            ),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/catalog/books?search=martin")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Clean Architecture"

    res2 = await client.get("/api/catalog/books?publisher=Addison-Wesley")
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["total"] == 1
    assert data2["items"][0]["authors"] == "Eric Evans"
