# === tests/api/catalog/test_get_book.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem


@pytest.mark.asyncio
async def test_get_book_success(client: AsyncClient, db_session: AsyncSession):
    """Should return book details and availability for an existing record."""
    book = Book(
        isbn="9781111111111",
        title="Fluent Python",
        authors="Luciano Ramalho",
        publisher="O'Reilly Media",
        published_date="2022-03-15",
        thumbnail="https://example.com/fluent.jpg",
        description="Python deep dive.",
        source="imported",
    )
    db_session.add(book)
    db_session.add(BookItem(isbn=book.isbn, is_available=True, current_location="library"))
    await db_session.commit()

    res = await client.get(f"/api/catalog/books/{book.isbn}")
    assert res.status_code == 200
    data = res.json()
    assert data["isbn"] == book.isbn
    assert data["title"] == "Fluent Python"
    assert data["available_count"] == 1


@pytest.mark.asyncio
async def test_get_book_not_found(client: AsyncClient):
    """Should return 404 response when book is not found."""
    res = await client.get("/api/catalog/books/9999999999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Book not found"
