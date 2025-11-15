# === models/user.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import user_role_enum

if TYPE_CHECKING:
    from models.cart import Cart
    from models.order import Order


class User(Base):
    """Represents a user in the BookDrop system."""

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique user identifier.",
    )

    email: Mapped[str] = mapped_column(
        String, nullable=False, comment="User login email (lowercased by DB trigger)."
    )

    password: Mapped[str] = mapped_column(String, nullable=False, comment="Hashed password.")

    role: Mapped[str] = mapped_column(
        user_role_enum, nullable=False, comment="User role: reader, librarian, or courier."
    )

    first_name: Mapped[str] = mapped_column(String, nullable=False, comment="User first name.")

    last_name: Mapped[str] = mapped_column(String, nullable=False, comment="User last name.")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Account creation timestamp.",
    )

    orders: Mapped[list["Order"]] = relationship(
        back_populates="reader", cascade="all, delete-orphan", lazy="selectin"
    )

    cart: Mapped["Cart"] = relationship(back_populates="user", uselist=False)

    __table_args__ = (
        Index("idx_user_role", "role"),
        Index("uq_user_email_lower", text("LOWER(email)"), unique=True),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the user."""
        return f"<User(id={self.id}, email='{self.email}', role='{self.role}')>"
