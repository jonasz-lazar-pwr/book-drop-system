# === routers/librarian.py ===
"""
Librarian API routes for BookDrop.

Endpoints:
- GET /api/librarian/orders — List all orders placed by readers.
- GET /api/librarian/orders/{order_id} — Retrieve details of a specific order,
  including requested titles and available physical book copies.
- POST /api/librarian/orders/{order_id}/assign-items — Assign physical book copies
  (BookItem) to an order.
- GET /api/librarian/orders/{order_id}/summary — Get full summary of an order
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from core.roles import require_role
from models import User
from repositories.librarian_repository import LibrarianRepository
from schemas.librarian import (
    AssignItemsRequest,
    LibrarianOrderDetailsResponse,
    LibrarianOrderListResponse,
    LibrarianOrderSummaryResponse,
    SimpleMessageResponse,
)

router = APIRouter(tags=["Librarian"])

require_librarian = require_role("librarian")


@router.get(
    "/orders",
    response_model=list[LibrarianOrderListResponse],
    summary="List all orders",
    description=(
        "Returns a list of all orders in the system, including basic information such as "
        "order ID, reader ID, status, and creation timestamp. "
        "Available only to librarians."
    ),
    responses={
        200: {"description": "List of orders returned successfully."},
        401: {"description": "Authentication required."},
        403: {"description": "Only librarians are allowed to access this endpoint."},
    },
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Return a complete list of all orders."""
    return await LibrarianRepository.list_orders(db)


@router.get(
    "/orders/{order_id}",
    summary="Get order details",
    response_model=LibrarianOrderDetailsResponse,
    description=(
        "Returns detailed information about a specific order, including: "
        "- requested books (ISBN, title, quantity),\n"
        "- available physical copies (BookItem) grouped by ISBN.\n\n"
        "Used by the librarian to decide which physical copies should be assigned."
    ),
    responses={
        200: {"description": "Order details returned successfully."},
        401: {"description": "Authentication required."},
        403: {"description": "Only librarians are allowed to access this endpoint."},
        404: {"description": "Order not found."},
    },
)
async def order_details(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Retrieve detailed order info including requested titles and available book items."""
    return await LibrarianRepository.get_order_details(db, order_id)


@router.post(
    "/orders/{order_id}/assign-items",
    summary="Assign book items to an order",
    response_model=SimpleMessageResponse,
    description=(
        "Assigns specific physical copies (BookItem) to an order based on the librarian's selection. "
        "Each entry contains an ISBN and the list of BookItem IDs that should be linked to the order.\n\n"
        "The system automatically updates book-item availability and marks the order as `prepared`."
    ),
    responses={
        200: {"description": "Book items successfully assigned."},
        400: {"description": "One or more BookItem IDs are invalid or unavailable."},
        401: {"description": "Authentication required."},
        403: {"description": "Only librarians are allowed to access this endpoint."},
        404: {"description": "Order not found."},
    },
)
async def assign_items(
    order_id: str,
    body: AssignItemsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Assign selected physical book items to the order."""
    return await LibrarianRepository.assign_items(db, order_id, body)


@router.get(
    "/orders/{order_id}/summary",
    summary="Get full librarian order summary",
    response_model=LibrarianOrderSummaryResponse,
    description=(
        "Returns complete information about an order for librarians. "
        "Includes reader info, book metadata and assigned physical copies. "
        "Works for all statuses except 'new'."
    ),
    responses={
        200: {"description": "Order summary returned successfully."},
        400: {"description": "Order is still NEW — no summary yet."},
        401: {"description": "Authentication required."},
        403: {"description": "Only librarians are allowed."},
        404: {"description": "Order not found."},
    },
)
async def order_summary(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Return full summary for this order."""
    return await LibrarianRepository.get_order_summary(db, order_id)
