# === schemas/librarian.py ===

from typing import Dict, List

from pydantic import BaseModel


class LibrarianOrderListResponse(BaseModel):
    """Row returned in the librarian order list."""

    order_id: str
    reader_id: str
    reader_email: str
    reader_first_name: str
    reader_last_name: str
    status: str
    created_at: str


class OrderBookInfo(BaseModel):
    """Requested book info used in order details."""

    isbn: str
    quantity: int
    title: str


class AvailableBookItem(BaseModel):
    """Physical book item available for assignment."""

    id: str
    location: str
    is_available: bool


class LibrarianOrderDetailsResponse(BaseModel):
    """Full details needed for assigning book copies."""

    order_id: str
    status: str
    created_at: str
    reader_email: str
    reader_first_name: str
    reader_last_name: str
    books: List[OrderBookInfo]
    available_items: Dict[str, List[AvailableBookItem]]


class AssignItemEntry(BaseModel):
    """Single ISBN assignment entry."""

    isbn: str
    book_item_ids: List[str]


class AssignItemsRequest(BaseModel):
    """Bulk assignment request payload."""

    items: List[AssignItemEntry]


class SimpleMessageResponse(BaseModel):
    """Simple one-field success response."""

    message: str


class LibrarianOrderSummaryBook(BaseModel):
    """Single prepared order book entry."""

    isbn: str
    title: str
    authors: str
    publisher: str | None
    published_date: str | None
    quantity: int
    assigned_items: List[str]


class LibrarianOrderSummaryReader(BaseModel):
    """Reader info included in order summary."""

    first_name: str
    last_name: str
    email: str


class LibrarianOrderSummaryResponse(BaseModel):
    """Complete prepared order summary."""

    order_id: str
    status: str
    created_at: str
    reader: LibrarianOrderSummaryReader
    books: List[LibrarianOrderSummaryBook]
