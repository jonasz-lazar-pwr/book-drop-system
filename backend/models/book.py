# === models/book.py ===

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.book_item import BookItem


class Book(Base):
    """Represents a book in the library catalog."""

    __tablename__ = "book"

    isbn: Mapped[str] = mapped_column(Text, primary_key=True, comment="Unique ISBN identifier.")
    title: Mapped[str] = mapped_column(Text, nullable=False, comment="Book title.")
    authors: Mapped[str] = mapped_column(Text, nullable=False, comment="Comma-separated authors.")
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Book publisher.")
    published_date: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Publication date."
    )
    thumbnail: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="URL to cover thumbnail."
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Book description."
    )
    source: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Data source name.")

    items: Mapped[list["BookItem"]] = relationship(
        back_populates="book", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        Index("idx_book_title", text("to_tsvector('simple', title)"), postgresql_using="gin"),
        Index("idx_book_authors", text("to_tsvector('simple', authors)"), postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        """Return a readable representation of the book."""
        return f"<Book(isbn='{self.isbn}', title='{self.title}')>"
