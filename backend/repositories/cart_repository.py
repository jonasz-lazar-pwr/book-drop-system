# === repositories/cart_repository.py ===

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book, BookItem, Cart, CartItem, CartStatus


class CartRepository:
    """Handles async database operations related to user carts."""

    @staticmethod
    async def ensure_cart(db: AsyncSession, user_id: str) -> Cart:
        """Return user's active cart or create one if it doesn't exist."""
        result = await db.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            cart = Cart(user_id=user_id, status=CartStatus.ACTIVE)
            db.add(cart)
            await db.flush()
        return cart

    @staticmethod
    async def get_cart(db: AsyncSession, user_id: str):
        """Fetch the active cart with item and availability details."""
        cart = await CartRepository.ensure_cart(db, user_id)
        await db.refresh(cart)
        stmt = (
            select(
                Cart.id,
                Cart.user_id,
                CartItem.isbn,
                Book.title,
                Book.authors,
                Book.thumbnail,
                CartItem.quantity,
                func.count(BookItem.id)
                .filter(and_(BookItem.isbn == CartItem.isbn, BookItem.is_available.is_(True)))
                .label("available_count"),
            )
            .join(CartItem, Cart.id == CartItem.cart_id, isouter=True)
            .join(Book, Book.isbn == CartItem.isbn, isouter=True)
            .outerjoin(BookItem, BookItem.isbn == Book.isbn)
            .where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
            .group_by(
                Cart.id,
                Cart.user_id,
                CartItem.isbn,
                Book.title,
                Book.authors,
                Book.thumbnail,
                CartItem.quantity,
            )
        )
        result = await db.execute(stmt)
        rows = result.mappings().all()
        items = [
            {
                "isbn": row["isbn"],
                "title": row["title"],
                "authors": row["authors"],
                "thumbnail": row["thumbnail"],
                "quantity": row["quantity"],
                "available_count": row["available_count"] or 0,
            }
            for row in rows
            if row["isbn"]
        ]
        return {
            "id": cart.id,
            "user_id": user_id,
            "items": items,
            "total_items": sum(i["quantity"] for i in items),
        }

    @staticmethod
    async def add_item(db: AsyncSession, user_id: str, isbn: str):
        """Add a book to the cart or increase its quantity."""
        book = await db.scalar(select(Book).where(Book.isbn == isbn))
        if not book:
            raise HTTPException(status_code=404, detail="Book not found.")
        available_count = await db.scalar(
            select(func.count(BookItem.id)).where(
                BookItem.isbn == isbn, BookItem.is_available.is_(True)
            )
        )
        if not available_count:
            raise HTTPException(status_code=400, detail="No available copies left.")
        cart = await CartRepository.ensure_cart(db, user_id)
        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cannot modify a submitted cart.")
        result = await db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.isbn == isbn)
        )
        item = result.scalar_one_or_none()
        if item:
            if item.quantity >= available_count:
                raise HTTPException(
                    status_code=400, detail="Cannot add more copies than available."
                )
            item.quantity += 1
            message = "Quantity increased."
        else:
            db.add(CartItem(cart_id=cart.id, isbn=isbn, quantity=1))
            message = "Book added to cart."
        await db.commit()
        response = await CartRepository.get_cart(db, user_id)
        response["message"] = message
        return response

    @staticmethod
    async def update_quantity(db: AsyncSession, user_id: str, isbn: str, quantity: int):
        """Update the quantity of a specific book in the cart."""
        if quantity < 1:
            raise HTTPException(status_code=400, detail="Quantity must be positive.")
        cart = await CartRepository.ensure_cart(db, user_id)
        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cannot modify a submitted cart.")
        result = await db.execute(
            select(CartItem).where(CartItem.cart_id == cart.id, CartItem.isbn == isbn)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found.")
        available_count = await db.scalar(
            select(func.count(BookItem.id)).where(
                BookItem.isbn == isbn, BookItem.is_available.is_(True)
            )
        )
        if available_count and quantity > available_count:
            raise HTTPException(status_code=400, detail="Requested quantity exceeds availability.")
        item.quantity = quantity
        await db.commit()
        response = await CartRepository.get_cart(db, user_id)
        response["message"] = "Quantity updated."
        return response

    @staticmethod
    async def remove_item(db: AsyncSession, user_id: str, isbn: str):
        """Remove a book from the user's cart."""
        cart = await CartRepository.ensure_cart(db, user_id)
        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cannot modify a submitted cart.")
        result = await db.execute(
            delete(CartItem)
            .where(CartItem.cart_id == cart.id, CartItem.isbn == isbn)
            .returning(CartItem.isbn)
        )
        deleted = result.scalar_one_or_none()
        if not deleted:
            raise HTTPException(status_code=404, detail="Item not found.")
        await db.commit()
        response = await CartRepository.get_cart(db, user_id)
        response["message"] = "Item removed."
        return response

    @staticmethod
    async def clear_cart(db: AsyncSession, user_id: str):
        """Remove all items from the user's active cart."""
        cart = await CartRepository.ensure_cart(db, user_id)
        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Cannot modify a submitted cart.")
        await db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
        await db.commit()
        response = await CartRepository.get_cart(db, user_id)
        response["message"] = "Cart cleared."
        return response

    @staticmethod
    async def prepare_for_checkout(db: AsyncSession, user_id: str):
        """Validate user's active cart (check availability without locking)."""
        result = await db.execute(
            select(Cart)
            .where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
            .order_by(Cart.created_at.desc())
            .limit(1)
        )
        cart = result.scalar_one_or_none()
        if not cart:
            raise HTTPException(status_code=400, detail="No active cart found.")

        await db.refresh(cart, attribute_names=["items"])
        if not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        unavailable = []
        for item in cart.items:
            available_count = await db.scalar(
                select(func.count(BookItem.id)).where(
                    BookItem.isbn == item.isbn, BookItem.is_available.is_(True)
                )
            )
            if available_count < item.quantity:
                book = await db.scalar(select(Book).where(Book.isbn == item.isbn))
                unavailable.append(book.title if book else item.isbn)

        if unavailable:
            raise HTTPException(
                status_code=400,
                detail=f"The following books are no longer available: {', '.join(unavailable)}",
            )

        return {
            "cart_id": str(cart.id),
            "user_id": user_id,
            "total_items": sum(i.quantity for i in cart.items),
            "distinct_titles": len(cart.items),
            "message": "Cart validated successfully. Proceed to checkout.",
        }
