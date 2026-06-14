# schemas/order.py

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class InitiateReturnRequest(BaseModel):
    """Request body for initiating a return."""

    locker_id: UUID


class LockerResponse(BaseModel):
    """Locker information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    locker_code: str
    street: str
    city: str
    postal_code: str
    latitude: float
    longitude: float


class LockerShipmentResponse(BaseModel):
    """Shipment details with locker info."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    locker: LockerResponse
    mode: str  # 'delivery' | 'return'
    status: str  # ShipmentStatus enum
    pickup_code: str
    placed_at: Optional[datetime] = None
    created_at: datetime


class OrderItemResponse(BaseModel):
    """Single order item (book copy)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    book_item_id: UUID
    isbn: str
    title: str
    authors: str
    publisher: Optional[str] = None
    thumbnail: Optional[str] = None
    due_date: Optional[datetime] = None
    returned_at: Optional[datetime] = None


class OrderResponse(BaseModel):
    """Order with items and shipment."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reader_id: UUID
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    items: List[OrderItemResponse]
    shipment: Optional[LockerShipmentResponse] = None


class MessageResponse(BaseModel):
    """Generic success message."""

    message: str
