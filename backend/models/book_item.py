# === models/book_item.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import BookLocation, book_location_enum

if TYPE_CHECKING:
    from models.book import Book
    from models.order_item import OrderItem


class BookItem(Base):
    """Represents a single physical book copy."""

    __tablename__ = "book_item"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique identifier for this physical copy.",
    )

    isbn: Mapped[str] = mapped_column(
        ForeignKey("book.isbn", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        comment="Reference to the parent book record.",
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="Indicates if the copy is currently available.",
    )

    current_location: Mapped[BookLocation] = mapped_column(
        book_location_enum,
        nullable=False,
        server_default=text("'library'"),
        comment="Physical location of the book copy.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Timestamp when the copy was added to the system.",
    )

    book: Mapped["Book"] = relationship(back_populates="items", lazy="joined")
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="book_item", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_book_item_isbn", "isbn"),
        Index("idx_book_item_availability", "is_available"),
        Index("idx_book_item_location", "current_location"),
    )

    def __repr__(self) -> str:
        """Return a readable representation of the book copy."""
        return (
            f"<BookItem(id={self.id}, isbn='{self.isbn}', "
            f"available={self.is_available}, location='{self.current_location.value}')>"
        )
