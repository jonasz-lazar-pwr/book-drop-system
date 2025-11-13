# === repositories/cart_repository.py ===

from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BookItem, Cart, CartItem


class CartRepository:
    """Handles database operations for user carts."""

    @staticmethod
    async def add_item(db: AsyncSession, user_id: UUID, isbn: str, quantity: int = 1):
        """Add an available book copy to the user's cart."""
        available = await db.execute(
            select(BookItem).where(BookItem.isbn == isbn, BookItem.is_available.is_(True)).limit(1)
        )
        book_item = available.scalar_one_or_none()
        if not book_item:
            return None

        cart_result = await db.execute(select(Cart).where(Cart.user_id == user_id))
        cart = cart_result.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=str(user_id))
            db.add(cart)
            await db.flush()
            await db.refresh(cart)

        stmt = insert(CartItem).values(
            cart_id=cart.id,
            isbn=isbn,
            quantity=quantity,
        )
        await db.execute(stmt)
        await db.commit()
        return book_item

    @staticmethod
    async def remove_item(db: AsyncSession, user_id: UUID, item_id: str):
        """Remove a cart item belonging to a specific user."""
        stmt = (
            delete(CartItem).where(CartItem.id == item_id).where(CartItem.cart.has(user_id=user_id))
        )
        await db.execute(stmt)
        await db.commit()

    @staticmethod
    async def list_items(db: AsyncSession, user_id: UUID):
        """Return all items in a user's cart."""
        stmt = (
            select(CartItem)
            .join(Cart)
            .where(Cart.user_id == user_id)
            .order_by(CartItem.added_at.desc())
        )
        result = await db.execute(stmt)
        return result.scalars().all()
