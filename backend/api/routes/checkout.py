# === routers/checkout.py ===

"""
Checkout API routes for BookDrop.

Endpoints:
- GET /api/checkout/summary — Retrieve a summary of the user's submitted cart before order creation.
- GET /api/checkout/lockers — List available lockers (with optional city, postal code or radius filter).
- POST /api/checkout/submit — Finalize checkout, create order, and assign shipment to a locker box.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_current_user, get_db
from models import User
from repositories.checkout_repository import CheckoutRepository
from schemas.checkout import (
    CheckoutSubmitRequest,
    CheckoutSubmitResponse,
    CheckoutSummaryResponse,
    LockerResponse,
)

router = APIRouter(tags=["Checkout"])


@router.get(
    "/summary",
    response_model=CheckoutSummaryResponse,
    summary="Get checkout summary",
    description=(
        "Returns details of the user's submitted cart, including user info and "
        "the list of books that will be included in the order. "
        "This endpoint is available only after `/api/cart/prepare-order` has locked the cart."
    ),
    responses={
        200: {"description": "Checkout summary returned successfully."},
        400: {"description": "No submitted cart found."},
        401: {"description": "Authentication required."},
    },
)
async def get_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve submitted cart summary for the current user."""
    return await CheckoutRepository.get_summary(db, str(current_user.id))


@router.get(
    "/lockers",
    response_model=list[LockerResponse],
    summary="List available lockers",
    description=(
        "Returns all available lockers. "
        "Supports filtering by city or postal code, optionally by geographic radius (lat/lon + radius in km)."
    ),
    responses={
        200: {"description": "List of lockers returned successfully."},
        400: {"description": "Invalid geographic parameters."},
    },
)
async def list_lockers(
    city: str | None = Query(None, description="Filter lockers by city name (case-insensitive)."),
    postal_code: str | None = Query(None, description="Filter lockers by postal code."),
    lat: float | None = Query(None, description="Latitude for radius search."),
    lon: float | None = Query(None, description="Longitude for radius search."),
    radius: float | None = Query(None, description="Search radius in kilometers."),
    limit: int | None = Query(20, description="Maximum number of lockers to return (default: 20)."),
    db: AsyncSession = Depends(get_db),
):
    """Return list of lockers filtered by city, postal code, or geographic radius."""
    return await CheckoutRepository.list_lockers(
        db=db,
        city=city,
        postal_code=postal_code,
        lat=lat,
        lon=lon,
        radius=radius,
        limit=limit,
    )


@router.post(
    "/submit",
    response_model=CheckoutSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit checkout and create order",
    description=(
        "Finalizes the checkout process by creating an order, its associated items, "
        "and assigning a shipment to a random available locker box within the chosen locker. "
        "Marks the locker box as occupied and generates a unique pickup code."
    ),
    responses={
        201: {"description": "Order and shipment successfully created."},
        400: {
            "description": "No submitted cart found or no available locker boxes in the selected locker."
        },
        401: {"description": "Authentication required."},
    },
)
async def submit_checkout(
    body: CheckoutSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create order, assign shipment to locker, and finalize checkout."""
    return await CheckoutRepository.submit_checkout(db, str(current_user.id), body.locker_id)
