# === models/order_requested_item.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.book import Book
    from models.order import Order


class OrderRequestedItem(Base):
    __tablename__ = "order_requested_item"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order.id", ondelete="CASCADE"),
        nullable=False,
    )

    isbn: Mapped[str] = mapped_column(
        ForeignKey("book.isbn", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )

    quantity: Mapped[int] = mapped_column(
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    order: Mapped["Order"] = relationship(
        back_populates="requested_items",
        lazy="joined",
    )

    book: Mapped["Book"] = relationship(
        back_populates="requested_items",
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_requested_quantity_positive"),
        Index("idx_order_requested_order", "order_id"),
        Index("idx_order_requested_isbn", "isbn"),
    )

    def __repr__(self) -> str:
        """Return a debug representation of the requested item."""
        return (
            f"<OrderRequestedItem(id={self.id}, order_id={self.order_id}, "
            f"isbn='{self.isbn}', quantity={self.quantity})>"
        )
