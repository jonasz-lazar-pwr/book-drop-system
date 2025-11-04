# === models/cart_item.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.book import Book
    from models.cart import Cart


class CartItem(Base):
    """Represents a single book item within a user's cart."""

    __tablename__ = "cart_item"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique identifier for the cart item.",
    )

    cart_id: Mapped[str] = mapped_column(
        ForeignKey("cart.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the parent cart.",
    )

    isbn: Mapped[str] = mapped_column(
        ForeignKey("book.isbn"), nullable=False, comment="ISBN of the selected book."
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("1"),
        comment="Quantity of this book in the cart.",
    )

    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Timestamp when the item was added.",
    )

    cart: Mapped["Cart"] = relationship(back_populates="items", lazy="joined")
    book: Mapped["Book"] = relationship(lazy="joined")

    __table_args__ = (
        UniqueConstraint("cart_id", "isbn", name="uq_cart_item_cart_isbn"),
        CheckConstraint("quantity > 0", name="ck_cart_item_quantity_positive"),
        Index("idx_cart_item_cart_id", "cart_id"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the cart item."""
        return f"<CartItem(id={self.id}, cart_id={self.cart_id}, isbn='{self.isbn}', quantity={self.quantity})>"
