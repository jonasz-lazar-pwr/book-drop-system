# === models/base.py ===

from typing import ClassVar

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Declarative base class for all ORM models in BookDrop."""

    metadata = metadata
    __mapper_args__: ClassVar[dict] = {"eager_defaults": True}

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        """Return the table name as lowercase class name."""
        return cls.__name__.lower()

    def __repr__(self) -> str:
        """Return a generic string representation for debugging."""
        return f"<{self.__class__.__name__}(id={getattr(self, 'id', 'N/A')})>"
