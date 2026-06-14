"""
Librarian API routes for BookDrop.
"""

from uuid import UUID

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
)
async def list_orders(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Return a complete list of all orders."""
    return await LibrarianRepository.list_orders(db)


@router.get(
    "/orders/{order_id}",
    response_model=LibrarianOrderDetailsResponse,
    summary="Get order details for assignment",
    description=(
        "Returns detailed information about a NEW order, including: "
        "- requested books (ISBN, title, quantity)\n"
        "- available physical copies (BookItem) grouped by ISBN\n\n"
        "Used by the librarian to assign physical copies."
    ),
)
async def get_order_details(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Retrieve order details for assignment."""
    return await LibrarianRepository.get_order_details(db, order_id)


@router.post(
    "/orders/{order_id}/assign-items",
    response_model=SimpleMessageResponse,
    summary="Assign book items to order",
    description=(
        "Assigns specific physical copies (BookItem) to a NEW order. "
        "Automatically updates book-item availability and marks order as `prepared`."
    ),
)
async def assign_items(
    order_id: UUID,
    body: AssignItemsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Assign selected physical book items to the order."""
    return await LibrarianRepository.assign_items(db, order_id, body)


@router.get(
    "/orders/{order_id}/summary",
    response_model=LibrarianOrderSummaryResponse,
    summary="Get order summary",
    description=(
        "Returns complete order information for librarians. "
        "Includes reader info, book metadata, and assigned physical copies. "
        "Works for all statuses except 'new'."
    ),
)
async def get_order_summary(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """Return full summary for this order."""
    return await LibrarianRepository.get_order_summary(db, order_id)


# ============================================
# ✅ NOWY ENDPOINT - ACCEPT RETURN
# ============================================


@router.post(
    "/orders/{order_id}/accept_return",
    response_model=SimpleMessageResponse,
    summary="Accept book return",
    description=(
        "Confirms that returned books have been received and checked by librarian. "
        "Changes order status from `return_in_progress` to `returned` and "
        "makes book items available again in library inventory."
    ),
)
async def accept_return(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_librarian),
):
    """
    Accept returned books from reader.

    Flow:
    1. Validate order status is 'return_in_progress'
    2. Validate return shipment status is 'placed_in_locker'
    3. Mark shipment as 'completed'
    4. Mark order as 'returned'
    5. Set returned_at for all OrderItems
    6. Release BookItems (available=True, location=library)
    """
    return await LibrarianRepository.accept_return(db, order_id)
