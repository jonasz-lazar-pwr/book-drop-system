# === routers/cart.py ===

"""
Shopping cart API routes for BookDrop.

Endpoints:
- GET /api/cart — Retrieve the current user's active cart.
- POST /api/cart/items — Add a book to the cart (creates cart if needed).
- PATCH /api/cart/items/{isbn} — Update quantity of a specific book.
- DELETE /api/cart/items/{isbn} — Remove a book from the cart.
- DELETE /api/cart/clear — Remove all items from the cart.
- POST /api/cart/prepare-order — Lock cart and prepare for checkout.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models import User
from repositories.cart_repository import CartRepository
from schemas.cart import AddItemRequest, CartResponse, UpdateQuantityRequest

router = APIRouter(tags=["Cart"])


@router.get(
    "",
    response_model=CartResponse,
    summary="Get current cart",
    description=(
        "Returns the currently active cart for the authenticated user. "
        "If no cart exists, an empty one is automatically created."
    ),
    responses={
        200: {"description": "Cart retrieved successfully."},
        401: {"description": "Authentication required."},
    },
)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve the active cart for the current user."""
    return await CartRepository.get_cart(db, str(current_user.id))


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    summary="Add book to cart",
    description=(
        "Adds a book to the user's active cart. "
        "If the book already exists in the cart, increments its quantity by 1."
    ),
)
async def add_item(
    payload: AddItemRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a book to the current user's cart."""
    return await CartRepository.add_item(db, str(current_user.id), payload.isbn)


@router.patch(
    "/items/{isbn}",
    response_model=CartResponse,
    summary="Update quantity",
    description="Updates the quantity of a given book in the user's active cart.",
    responses={
        200: {"description": "Quantity updated successfully."},
        400: {"description": "Invalid quantity value."},
        404: {"description": "Item not found in the cart."},
    },
)
async def update_quantity(
    isbn: str,
    payload: UpdateQuantityRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the quantity of a specific book in the cart."""
    return await CartRepository.update_quantity(db, str(current_user.id), isbn, payload.quantity)


@router.delete(
    "/items/{isbn}",
    response_model=CartResponse,
    summary="Remove book from cart",
    description="Removes a specific book from the user's active cart.",
    responses={
        200: {"description": "Item removed successfully."},
        404: {"description": "Book not found in cart."},
    },
)
async def remove_item(
    isbn: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a book from the current user's cart."""
    return await CartRepository.remove_item(db, str(current_user.id), isbn)


@router.delete(
    "/clear",
    response_model=CartResponse,
    summary="Clear cart",
    description="Removes all books from the user's active cart.",
    responses={200: {"description": "Cart cleared successfully."}},
)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove all items from the current user's cart."""
    return await CartRepository.clear_cart(db, str(current_user.id))


@router.post(
    "/prepare-order",
    status_code=status.HTTP_200_OK,
    summary="Prepare cart for checkout",
    description=(
        "Locks the current cart for checkout. "
        "Does not create an order yet — returns cart summary for the next step."
    ),
)
async def prepare_order(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate and lock the cart before checkout."""
    return await CartRepository.prepare_for_checkout(db, str(current_user.id))
