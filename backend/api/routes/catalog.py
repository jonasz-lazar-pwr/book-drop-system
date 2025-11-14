# === routers/catalog.py ===

"""
Catalog API routes for BookDrop.

Endpoints:
- GET /api/catalog/books — Paginated and filtered list of books.
- GET /api/catalog/books/{isbn} — Detailed info for a specific book.
- GET /api/catalog/publishers — List of publishers.
- POST /api/catalog/books/{isbn}/cart — Add a book to user's cart (requires login).
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from repositories.catalog_repository import CatalogRepository
from schemas.catalog import (
    BookDetail,
    BookListItem,
    BookListResponse,
    CatalogFilters,
)

router = APIRouter(tags=["Catalog"])


@router.get(
    "/books",
    response_model=BookListResponse,
    summary="List books with pagination and filters",
    description="Returns a paginated list of books with optional search, filters and sorting.",
)
async def list_books(
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1, le=100),
    filters: CatalogFilters = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Return paginated catalog with filters and sorting."""
    rows, total = await CatalogRepository.list_books(db, page=page, limit=limit, filters=filters)
    return BookListResponse(items=[BookListItem(**row) for row in rows], total=total)


@router.get(
    "/books/{isbn}",
    response_model=BookDetail,
    summary="Get book details",
    description="Retrieve detailed information for a specific book by ISBN.",
)
async def get_book(isbn: str, db: AsyncSession = Depends(get_db)):
    """Return book details."""
    row = await CatalogRepository.get_book(db, isbn)
    if not row:
        raise HTTPException(status_code=404, detail="Book not found")
    book = row["Book"]
    return BookDetail(
        isbn=book.isbn,
        title=book.title,
        authors=book.authors,
        publisher=book.publisher,
        published_date=book.published_date,
        thumbnail=book.thumbnail,
        description=book.description,
        source=book.source,
        available_count=row["available_count"],
    )


@router.get(
    "/publishers",
    response_model=List[str],
    summary="List publishers",
    description="Returns a list of all unique publishers available in the catalog.",
)
async def list_publishers(db: AsyncSession = Depends(get_db)):
    """Return all publishers."""
    return await CatalogRepository.list_publishers(db)
