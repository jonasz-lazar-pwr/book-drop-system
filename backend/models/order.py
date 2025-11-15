# === models/order.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import order_status_enum

if TYPE_CHECKING:
    from models.locker_shipment import LockerShipment
    from models.order_item import OrderItem
    from models.order_requested_item import OrderRequestedItem
    from models.user import User


class Order(Base):
    """Represents a reader's book order."""

    __tablename__ = "order"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique order identifier.",
    )

    reader_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reader who placed the order.",
    )

    status: Mapped[str] = mapped_column(
        order_status_enum,
        nullable=False,
        server_default=text("'new'"),
        comment="Current order status.",
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Timestamp of the last status update."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Timestamp when the order was created.",
    )

    reader: Mapped["User"] = relationship(back_populates="orders", lazy="joined")

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    shipments: Mapped[list["LockerShipment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    requested_items: Mapped[list["OrderRequestedItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_order_reader", "reader_id"),
        Index("idx_order_status", "status"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the order."""
        return f"<Order(id={self.id}, reader_id={self.reader_id}, status='{self.status}')>"
