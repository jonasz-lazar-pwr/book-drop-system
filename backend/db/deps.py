# === db/deps.py ===

"""
Database dependency for FastAPI routes.

This module provides a reusable dependency (`get_db`) that yields
an asynchronous SQLAlchemy session. It is used in route handlers
to interact with the database.
"""

from .session import async_session

async def get_db():
    """
    Dependency that provides an async SQLAlchemy session.

    This function is used with FastAPI's `Depends` to inject
    the database session into routes and services.

    Yields:
        AsyncSession: An instance of SQLAlchemy asynchronous session.
    """
    async with async_session() as session:
        yield session
