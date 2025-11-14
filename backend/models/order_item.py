# === models/order_item.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.book_item import BookItem
    from models.order import Order


class OrderItem(Base):
    """Represents one physical book copy borrowed within an order."""

    __tablename__ = "order_item"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique order item identifier.",
    )

    order_id: Mapped[str] = mapped_column(
        ForeignKey("order.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent order reference.",
    )

    book_item_id: Mapped[str | None] = mapped_column(
        ForeignKey("book_item.id"),
        nullable=True,
        comment="Assigned physical book copy (may be NULL until librarian assigns).",
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Expected return date for this book copy."
    )

    returned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Actual return date for this book copy."
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Timestamp when this record was created.",
    )

    order: Mapped["Order"] = relationship(back_populates="items", lazy="joined")
    book_item: Mapped["BookItem"] = relationship(back_populates="order_items", lazy="joined")

    __table_args__ = (
        UniqueConstraint("book_item_id", name="uq_book_item_once"),
        CheckConstraint("(returned_at IS NULL OR returned_at >= due_date)", name="ck_order_dates"),
        Index("idx_order_item_order", "order_id"),
        Index("idx_order_item_book_item", "book_item_id"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the order item."""
        return (
            f"<OrderItem(id={self.id}, order_id={self.order_id}, "
            f"book_item_id={self.book_item_id or 'None'}, due_date={self.due_date}, returned_at={self.returned_at})>"
        )
