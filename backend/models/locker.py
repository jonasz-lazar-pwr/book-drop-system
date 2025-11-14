# === models/locker.py ===

from __future__ import annotations

from typing import TYPE_CHECKING

from geoalchemy2 import Geography, WKBElement
from sqlalchemy import Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base

if TYPE_CHECKING:
    from models.locker_box import LockerBox
    from models.locker_shipment import LockerShipment


class Locker(Base):
    """Represents a parcel locker station with address and geolocation."""

    __tablename__ = "locker"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        comment="Unique locker identifier.",
    )

    locker_code: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        comment="Unique locker code (e.g., LOCKER-WRO-001).",
    )

    street: Mapped[str] = mapped_column(Text, nullable=False, comment="Street address.")
    city: Mapped[str] = mapped_column(Text, nullable=False, comment="City name.")
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False, comment="Postal code.")

    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False),
        nullable=False,
        comment="Locker coordinates (PostGIS POINT, WGS84).",
    )

    boxes: Mapped[list["LockerBox"]] = relationship(
        back_populates="locker", cascade="all, delete-orphan", lazy="selectin"
    )

    shipments: Mapped[list["LockerShipment"]] = relationship(
        "LockerShipment",
        secondary="locker_box",
        primaryjoin="Locker.id == LockerBox.locker_id",
        secondaryjoin="LockerBox.id == LockerShipment.locker_box_id",
        viewonly=True,
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_locker_city", "city"),
        Index("idx_locker_location", "location", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        """Return a readable string representation of the locker."""
        return f"<Locker(code='{self.locker_code}', city='{self.city}')>"
