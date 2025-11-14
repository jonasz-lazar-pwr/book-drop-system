# === schemas/checkout.py ===

from typing import List, Optional

from pydantic import BaseModel, Field


class CheckoutBookItem(BaseModel):
    """Represents a single book entry in the checkout summary."""

    isbn: str
    title: str
    authors: str
    quantity: int


class CheckoutSummaryResponse(BaseModel):
    """Response schema for checkout summary with user and book details."""

    user_id: str
    first_name: str
    last_name: str
    email: str
    total_items: int
    distinct_titles: int
    books: List[CheckoutBookItem]


class LockerResponse(BaseModel):
    """Represents an available locker with optional distance information."""

    id: str
    locker_code: str
    street: str
    city: str
    postal_code: str
    lat: float
    lon: float
    distance_km: Optional[float] = None


class CheckoutSubmitRequest(BaseModel):
    """Request schema for submitting a checkout with the chosen locker."""

    locker_id: str = Field(..., description="Chosen locker for delivery")


class CheckoutSubmitResponse(BaseModel):
    """Response schema returned after a successful checkout submission."""

    order_id: str
    shipment_id: str
    pickup_code: str
    locker_code: str
    city: str
    postal_code: str
    message: str
