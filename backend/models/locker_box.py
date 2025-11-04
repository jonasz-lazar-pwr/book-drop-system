# === models/locker_box.py ===

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.locker import Locker
    from models.locker_shipment import LockerShipment


class LockerBox(Base):
    """Represents a single compartment inside a locker."""

    __tablename__ = "locker_box"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique locker box identifier.",
    )

    locker_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("locker.id", ondelete="CASCADE"),
        nullable=False,
        comment="Reference to the parent locker.",
    )

    number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Sequential number of the box within its locker."
    )

    is_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
        comment="True if the box is free, false if occupied.",
    )

    locker: Mapped["Locker"] = relationship(back_populates="boxes", lazy="joined")
    shipments: Mapped[list["LockerShipment"]] = relationship(
        back_populates="locker_box", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("locker_id", "number", name="uq_locker_box_locker_number"),
        CheckConstraint("number > 0", name="ck_locker_box_number_positive"),
        Index("idx_locker_box_available", "is_available"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the locker box."""
        return f"<LockerBox(locker_id={self.locker_id}, number={self.number}, available={self.is_available})>"
