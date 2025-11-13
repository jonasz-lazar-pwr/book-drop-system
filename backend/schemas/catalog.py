# === schemas/catalog.py ===

from typing import List, Optional

from pydantic import BaseModel, Field


class BookListItem(BaseModel):
    """Response model for a single book item in the catalog list."""

    isbn: str
    title: str
    authors: str
    publisher: Optional[str]
    published_date: Optional[str]
    thumbnail: Optional[str]
    available_count: int = Field(default=0)


class BookListResponse(BaseModel):
    """Response model for paginated catalog of books."""

    items: List[BookListItem]
    total: int


class BookDetail(BaseModel):
    """Response model for detailed book information."""

    isbn: str
    title: str
    authors: str
    publisher: Optional[str]
    published_date: Optional[str]
    thumbnail: Optional[str]
    description: Optional[str]
    source: Optional[str]
    available_count: int


class AddToCartRequest(BaseModel):
    """Request model for adding a book to the user's cart."""

    quantity: int = Field(default=1, ge=1)


class AddToCartResponse(BaseModel):
    """Response model confirming a book was added to the cart."""

    message: str
    cart_item: dict


class CatalogFilters(BaseModel):
    """Query filters for listing books."""

    search: Optional[str] = None
    sort: Optional[str] = None
    publisher: Optional[str] = None
    available_only: bool = False
    year_from: Optional[int] = None
    year_to: Optional[int] = None
