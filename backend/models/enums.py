# === models/enums.py ===

from enum import StrEnum

from sqlalchemy import Enum as PgEnum


class UserRole(StrEnum):
    """Defines user roles in the system."""

    READER = "reader"
    LIBRARIAN = "librarian"
    COURIER = "courier"


user_role_enum = PgEnum("reader", "librarian", "courier", name="user_role", create_type=False)


class OrderStatus(StrEnum):
    """Defines all stages in the order lifecycle."""

    NEW = "new"
    PREPARED = "prepared"
    IN_TRANSIT = "in_transit"
    READY_FOR_PICKUP = "ready_for_pickup"
    PICKED_UP = "picked_up"
    RETURN_IN_PROGRESS = "return_in_progress"
    RETURNED = "returned"
    CANCELED = "canceled"


order_status_enum = PgEnum(
    "new",
    "prepared",
    "in_transit",
    "ready_for_pickup",
    "picked_up",
    "return_in_progress",
    "returned",
    "canceled",
    name="order_status",
    create_type=False,
)


class ShipmentMode(StrEnum):
    """Defines whether a shipment is a delivery or return."""

    DELIVERY = "delivery"
    RETURN_ = "return"  # “return” is reserved in Python


shipment_mode_enum = PgEnum("delivery", "return", name="shipment_mode", create_type=False)


class ShipmentStatus(StrEnum):
    """Defines shipment process stages."""

    CREATED = "created"
    PLACED_IN_LOCKER = "placed_in_locker"
    RETRIEVED_BY_USER = "retrieved_by_user"
    COLLECTED_BY_COURIER = "collected_by_courier"
    COMPLETED = "completed"


shipment_status_enum = PgEnum(
    "created",
    "placed_in_locker",
    "retrieved_by_user",
    "collected_by_courier",
    "completed",
    name="shipment_status",
    create_type=False,
)


class CartStatus(StrEnum):
    """Defines shopping cart states."""

    ACTIVE = "active"
    SUBMITTED = "submitted"


cart_status_enum = PgEnum("active", "submitted", name="cart_status", create_type=False)


class BookLocation(StrEnum):
    """Defines physical book locations."""

    LIBRARY = "library"
    TRANSIT = "transit"
    LOCKER = "locker"
    BORROWED = "borrowed"


book_location_enum = PgEnum(
    "library", "transit", "locker", "borrowed", name="book_location", create_type=False
)
