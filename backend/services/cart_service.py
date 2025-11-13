# === services/cart_service.py ===

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.cart_repository import CartRepository
from repositories.catalog_repository import CatalogRepository


class CartService:
    """High-level business logic for cart operations."""

    @staticmethod
    async def add_to_cart(db: AsyncSession, user_id: UUID, isbn: str, quantity: int = 1):
        book_row = await CatalogRepository.get_book(db, isbn)
        if not book_row:
            raise HTTPException(status_code=404, detail="Book not found")

        item = await CartRepository.add_item(db, user_id, isbn, quantity)
        if not item:
            raise HTTPException(status_code=400, detail="No available copies")

        return {"isbn": isbn, "title": book_row["Book"].title}
