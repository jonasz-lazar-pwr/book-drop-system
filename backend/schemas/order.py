# === schemas/oredr.py ===

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel

from models.enums import OrderStatus


class OrderItemSchema(BaseModel):
    """Represents one book copy inside an order."""

    id: Optional[UUID]
    book_item_id: Optional[UUID]
    due_date: Optional[datetime]
    returned_at: Optional[datetime]

    class Config:
        orm_mode = True


class OrderResponse(BaseModel):
    """Represents an order with its items."""

    id: UUID
    reader_id: UUID
    status: OrderStatus
    created_at: datetime
    updated_at: Optional[datetime]
    items: List[OrderItemSchema]

    class Config:
        orm_mode = True


class SubmitOrderResponse(BaseModel):
    """Response after submitting a cart into an order."""

    order_id: UUID
    detail: str
