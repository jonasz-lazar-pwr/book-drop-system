# === models/cart.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import CartStatus, cart_status_enum

if TYPE_CHECKING:
    from models.cart_item import CartItem
    from models.user import User


class Cart(Base):
    """Represents a shopping cart belonging to a single user."""

    __tablename__ = "cart"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique cart identifier.",
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="User who owns this cart.",
    )

    status: Mapped[CartStatus] = mapped_column(
        cart_status_enum,
        nullable=False,
        server_default=text("'active'"),
        comment="Cart status indicator.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Creation timestamp.",
    )

    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Last update timestamp.",
    )

    user: Mapped["User"] = relationship(back_populates="cart", lazy="joined")
    items: Mapped[List["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (Index("idx_cart_user_id", "user_id"),)

    def __repr__(self) -> str:
        """Return a readable string representation of the cart."""
        return f"<Cart(id={self.id}, user_id={self.user_id}, status='{self.status.value}')>"
