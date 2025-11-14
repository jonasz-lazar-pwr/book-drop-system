# === schemas/cart.py ===

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CartItemSchema(BaseModel):
    """Represents a single item inside the user's cart."""

    model_config = ConfigDict(from_attributes=True)

    isbn: str
    title: str
    authors: str
    thumbnail: Optional[str]
    quantity: int
    available_count: int


class CartResponse(BaseModel):
    """Response model for the entire user cart."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID]
    user_id: UUID
    items: List[CartItemSchema]
    total_items: int


class AddItemRequest(BaseModel):
    """Request payload for adding a book to the cart."""

    isbn: str


class UpdateQuantityRequest(BaseModel):
    """Request payload for updating quantity of a cart item."""

    quantity: int
