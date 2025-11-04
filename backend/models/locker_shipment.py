# === models/locker_shipment.py ===

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base
from models.enums import ShipmentMode, ShipmentStatus, shipment_mode_enum, shipment_status_enum

if TYPE_CHECKING:
    from models.locker_box import LockerBox
    from models.order import Order


class LockerShipment(Base):
    """Represents a single locker delivery or return operation."""

    __tablename__ = "locker_shipment"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique shipment identifier.",
    )

    order_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order.id", ondelete="CASCADE"),
        nullable=False,
        comment="Order associated with this shipment.",
    )

    locker_box_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locker_box.id"),
        nullable=False,
        comment="Locker box used for this operation.",
    )

    mode: Mapped[ShipmentMode] = mapped_column(
        shipment_mode_enum, nullable=False, comment="Operation type: delivery or return."
    )

    status: Mapped[ShipmentStatus] = mapped_column(
        shipment_status_enum, nullable=False, comment="Current logistics stage."
    )

    pickup_code: Mapped[str | None] = mapped_column(
        String(8), unique=True, nullable=True, comment="Unique 8-character pickup code."
    )

    placed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the parcel was placed in the locker.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="Record creation timestamp.",
    )

    order: Mapped["Order"] = relationship(back_populates="shipments", lazy="joined")
    locker_box: Mapped["LockerBox"] = relationship(back_populates="shipments", lazy="joined")

    locker = relationship(
        "Locker",
        secondary="locker_box",
        primaryjoin="LockerShipment.locker_box_id == LockerBox.id",
        secondaryjoin="LockerBox.locker_id == Locker.id",
        viewonly=True,
        lazy="joined",
    )

    __table_args__ = (
        CheckConstraint(
            "(pickup_code IS NULL OR char_length(pickup_code) = 8)", name="ck_pickup_code_length"
        ),
        Index("idx_shipment_order", "order_id"),
        Index("idx_shipment_mode", "mode"),
        Index("idx_shipment_status", "status"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the shipment."""
        return f"<LockerShipment(id={self.id}, mode='{self.mode.value}', status='{self.status.value}')>"
