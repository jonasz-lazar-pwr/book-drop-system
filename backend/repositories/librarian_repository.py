# === repositories/librarian_repository.py ===

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import BookItem, Order, OrderItem, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus


class LibrarianRepository:
    @staticmethod
    async def list_orders(db: AsyncSession):
        """Return a list of librarian-visible orders."""
        q = await db.execute(
            select(Order).join(User, User.id == Order.reader_id).order_by(Order.created_at.desc())
        )
        orders = q.scalars().all()

        return [
            {
                "order_id": str(o.id),
                "reader_id": str(o.reader.id),
                "reader_email": o.reader.email,
                "reader_first_name": o.reader.first_name,
                "reader_last_name": o.reader.last_name,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]

    @staticmethod
    async def get_order_details(db: AsyncSession, order_id: str):
        """Return order details with available book copies."""
        q = await db.execute(
            select(Order).where(Order.id == order_id).join(User, User.id == Order.reader_id)
        )
        order = q.scalar()

        if not order:
            raise HTTPException(404, "Order not found.")

        q_req = await db.execute(
            select(OrderRequestedItem).where(OrderRequestedItem.order_id == order_id)
        )
        requested_items = q_req.scalars().all()

        needed_books = [
            {
                "isbn": req.isbn,
                "quantity": req.quantity,
                "title": req.book.title,
            }
            for req in requested_items
        ]

        q_avail = await db.execute(select(BookItem).where(BookItem.is_available.is_(True)))

        available_by_isbn = {}
        for bi in q_avail.scalars().all():
            available_by_isbn.setdefault(bi.isbn, []).append(
                {
                    "id": str(bi.id),
                    "location": bi.current_location,
                    "is_available": bi.is_available,
                }
            )

        return {
            "order_id": str(order.id),
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "reader_email": order.reader.email,
            "reader_first_name": order.reader.first_name,
            "reader_last_name": order.reader.last_name,
            "books": needed_books,
            "available_items": available_by_isbn,
        }

    @staticmethod
    async def assign_items(db: AsyncSession, order_id: str, body):
        """Assign physical book items to an order."""
        order = await db.scalar(select(Order).where(Order.id == order_id))
        if not order:
            raise HTTPException(404, "Order not found.")

        for entry in body.items:
            book_item_ids = entry.book_item_ids

            for bi_id in book_item_ids:
                bi = await db.scalar(select(BookItem).where(BookItem.id == bi_id))
                if not bi:
                    raise HTTPException(400, f"BookItem {bi_id} not found.")
                if not bi.is_available:
                    raise HTTPException(400, f"BookItem {bi_id} not available.")

                oi = OrderItem(order_id=order.id, book_item_id=bi_id)
                db.add(oi)

                bi.is_available = False
                bi.current_location = BookLocation.TRANSIT
                db.add(bi)

        order.status = OrderStatus.PREPARED
        await db.commit()

        return {"message": "Book items assigned to order."}

    @staticmethod
    async def get_order_summary(db: AsyncSession, order_id: str):
        """Return a prepared order summary including assigned copies."""
        q = await db.execute(
            select(Order).where(Order.id == order_id).join(User, User.id == Order.reader_id)
        )
        order = q.scalar()

        if not order:
            raise HTTPException(404, "Order not found.")

        if order.status == OrderStatus.NEW:
            raise HTTPException(400, "Order is not prepared yet — no summary available.")

        q_req = await db.execute(
            select(OrderRequestedItem).where(OrderRequestedItem.order_id == order_id)
        )
        req_items = q_req.scalars().all()

        q_assigned = await db.execute(select(OrderItem).where(OrderItem.order_id == order_id))
        assigned_items = q_assigned.scalars().all()

        assigned_map: dict[str, list[str]] = {}

        for oi in assigned_items:
            bi = await db.scalar(select(BookItem).where(BookItem.id == oi.book_item_id))
            if bi:
                assigned_map.setdefault(bi.isbn, []).append(str(bi.id))

        books_out = []
        for req in req_items:
            books_out.append(
                {
                    "isbn": req.isbn,
                    "title": req.book.title,
                    "authors": req.book.authors,
                    "publisher": req.book.publisher,
                    "published_date": req.book.published_date,
                    "quantity": req.quantity,
                    "assigned_items": assigned_map.get(req.isbn, []),
                }
            )

        return {
            "order_id": str(order.id),
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "reader": {
                "first_name": order.reader.first_name,
                "last_name": order.reader.last_name,
                "email": order.reader.email,
            },
            "books": books_out,
        }
