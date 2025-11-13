# === services/books_importer.py ===

import logging
import secrets

import httpx

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from models import Book, BookItem

logger = logging.getLogger("books_importer")

GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


async def fetch_books_from_google(query: str, max_results: int):
    """Fetch a batch of Polish-language books from Google Books API."""
    params = {
        "q": query,
        "langRestrict": "pl",
        "maxResults": max_results,
        "printType": "books",
        "projection": "full",
        "orderBy": "relevance",
        "key": settings.GOOGLE_BOOKS_API_KEY,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(GOOGLE_BOOKS_URL, params=params)
        r.raise_for_status()
        data = r.json()
    return data.get("items", [])


def extract_book_info(item: dict):
    """Extract validated book metadata. Skip incomplete entries."""
    info = item.get("volumeInfo", {})
    if not info:
        return None

    # Require key fields
    if not all(
        [
            info.get("title"),
            info.get("authors"),
            info.get("publisher"),
            info.get("publishedDate"),
            info.get("description"),
        ]
    ):
        return None

    # Require valid ISBN
    isbn = None
    for idf in info.get("industryIdentifiers", []):
        if idf.get("type") in ("ISBN_13", "ISBN_10"):
            isbn = idf.get("identifier")
            break
    if not isbn:
        return None

    # Only accept Polish books
    lang = info.get("language", "").lower()
    if lang and lang != "pl":
        return None

    return {
        "isbn": isbn,
        "title": info["title"].strip(),
        "authors": ", ".join(info["authors"]),
        "publisher": info["publisher"].strip(),
        "published_date": info["publishedDate"].strip(),
        "thumbnail": (info.get("imageLinks") or {}).get("thumbnail"),
        "description": info["description"].strip(),
        "source": "google_books",
    }


async def import_books(db: AsyncSession, topics: list[str], limit_per_topic: int):
    """Fetch and insert valid Polish books with ISBN and full metadata."""
    inserted_count = 0

    for topic in topics:
        logger.info(f"Fetching books for topic: {topic}")
        books = await fetch_books_from_google(topic, limit_per_topic)

        for item in books:
            data = extract_book_info(item)
            if not data:
                continue

            existing = await db.execute(select(Book).where(Book.isbn == data["isbn"]))
            if existing.scalar_one_or_none():
                continue

            book = Book(**data)
            db.add(book)
            await db.flush()

            num_copies = secrets.randbelow(6) + 5
            for _ in range(num_copies):
                db.add(BookItem(isbn=book.isbn, is_available=True))

            inserted_count += 1

    await db.commit()
    logger.info(f"Inserted {inserted_count} fully qualified Polish books.")
    return inserted_count
