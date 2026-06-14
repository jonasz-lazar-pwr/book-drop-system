"""
Repository for librarian operations.
"""

from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import BookItem, Order, OrderItem, OrderRequestedItem, User
from models.enums import BookLocation, OrderStatus
from models.locker_shipment import LockerShipment


class LibrarianRepository:
    """Repository for librarian-specific operations."""

    # ============================================
    # LIST ORDERS
    # ============================================

    @staticmethod
    async def list_orders(db: AsyncSession) -> list[dict]:
        """
        Return a list of all orders with basic reader info.

        Returns:
            List of order dictionaries with reader details
        """
        stmt = (
            select(Order).join(User, User.id == Order.reader_id).order_by(Order.created_at.desc())
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

        return [
            {
                "order_id": str(order.id),
                "reader_id": str(order.reader.id),
                "reader_email": order.reader.email,
                "reader_first_name": order.reader.first_name,
                "reader_last_name": order.reader.last_name,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
            }
            for order in orders
        ]

    # ============================================
    # GET ORDER DETAILS (for NEW orders)
    # ============================================

    @staticmethod
    async def get_order_details(db: AsyncSession, order_id: UUID) -> dict:
        """
        Return order details with requested books and available copies.

        Args:
            db: Database session
            order_id: Order UUID

        Returns:
            Dictionary with order details, requested books, and available items

        Raises:
            HTTPException 404: Order not found
            HTTPException 400: Order is not in NEW status
        """
        # Fetch order with reader
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.reader))
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        if order.status != OrderStatus.NEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Order status is '{order.status}' - details only available for NEW orders",
            )

        # Fetch requested items
        stmt = (
            select(OrderRequestedItem)
            .where(OrderRequestedItem.order_id == order_id)
            .options(selectinload(OrderRequestedItem.book))
        )
        result = await db.execute(stmt)
        requested_items = result.scalars().all()

        needed_books = [
            {
                "isbn": req.isbn,
                "title": req.book.title,
                "quantity": req.quantity,
            }
            for req in requested_items
        ]

        # Fetch all available book items
        stmt = select(BookItem).where(BookItem.is_available.is_(True))
        result = await db.execute(stmt)
        available_items = result.scalars().all()

        # Group by ISBN
        available_by_isbn: dict[str, list[dict]] = {}
        for bi in available_items:
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

    # ============================================
    # ASSIGN ITEMS
    # ============================================

    @staticmethod
    async def assign_items(db: AsyncSession, order_id: UUID, body) -> dict:
        """
        Assign physical book items to an order.

        Flow:
        1. Validate order exists and is NEW
        2. Validate NO DUPLIKATY BookItems (uq_bookitem_once)
        3. Validate all BookItems exist and are available
        4. Create OrderItem links
        5. Mark BookItems as unavailable and in LOCKER
        6. Change order status to READY_FOR_PICKUP

        Args:
            db: Database session
            order_id: Order UUID
            body: AssignItemsRequest with items list

        Returns:
            Success message dictionary

        Raises:
            HTTPException 404: Order not found
            HTTPException 400: Invalid order status, duplicates, or unavailable items
        """
        # 1. Fetch order
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.unique().scalar_one_or_none()  # ✅ .unique()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        if order.status != OrderStatus.NEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot assign items: order status is '{order.status}' (expected 'new')",
            )

        # 2. ✅ WALIDACJA DUPLIKATÓW BookItem ID w całym body
        all_book_item_ids = []
        for entry in body.items:
            for bi_id in entry.book_item_ids:
                all_book_item_ids.append(bi_id)

        duplicates = [id for id in set(all_book_item_ids) if all_book_item_ids.count(id) > 1]
        if duplicates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplikat egzemplarza: {str(duplicates[0])[:8]}... (nie można przypisać tego samego egzemplarza wielokrotnie)",
            )

        # 3. ✅ WALIDACJA: BookItem NIE JEST JUŻ PRZYPISANY do żadnego OrderItem
        for entry in body.items:
            for bi_id in entry.book_item_ids:
                # Sprawdź czy BookItem już istnieje w OrderItem
                stmt = select(OrderItem).where(OrderItem.book_item_id == bi_id)
                result = await db.execute(stmt)
                existing_order_item = result.scalar_one_or_none()

                if existing_order_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Egzemplarz {str(bi_id)[:8]}... jest już przypisany do innego zamówienia",
                    )

        # 4. Validate and assign items
        for entry in body.items:
            for bi_id in entry.book_item_ids:
                # Fetch BookItem
                stmt = select(BookItem).where(BookItem.id == bi_id)
                result = await db.execute(stmt)
                book_item = result.unique().scalar_one_or_none()  # ✅ .unique()

                if not book_item:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"BookItem {str(bi_id)[:8]}... not found",
                    )

                if not book_item.is_available:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"BookItem {str(bi_id)[:8]}... is not available",
                    )

                # Create OrderItem link
                order_item = OrderItem(
                    order_id=order.id,
                    book_item_id=book_item.id,
                )
                db.add(order_item)

                # Update BookItem → LOCKER (MVP paczkomat)
                book_item.is_available = False
                book_item.current_location = BookLocation.LOCKER
                db.add(book_item)

        # 5. Update order status
        order.status = OrderStatus.READY_FOR_PICKUP
        order.updated_at = datetime.utcnow()

        await db.commit()

        return {"message": "Book items assigned successfully - gotowe w paczkomacie"}

    # ============================================
    # GET ORDER SUMMARY (for prepared+ orders)
    # ============================================

    @staticmethod
    async def get_order_summary(db: AsyncSession, order_id: UUID) -> dict:
        """
        Return complete order summary with assigned items.

        Args:
            db: Database session
            order_id: Order UUID

        Returns:
            Dictionary with reader info, books, and assigned items

        Raises:
            HTTPException 404: Order not found
            HTTPException 400: Order is still NEW
        """
        # Fetch order with reader
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.reader))
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        if order.status == OrderStatus.NEW:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is not prepared yet - no summary available",
            )

        # Fetch requested items
        stmt = (
            select(OrderRequestedItem)
            .where(OrderRequestedItem.order_id == order_id)
            .options(selectinload(OrderRequestedItem.book))
        )
        result = await db.execute(stmt)
        requested_items = result.scalars().all()

        # Fetch assigned items
        stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .options(selectinload(OrderItem.book_item))
        )
        result = await db.execute(stmt)
        assigned_items = result.scalars().all()

        # Build map of ISBN -> assigned BookItem IDs
        assigned_map: dict[str, list[str]] = {}
        for oi in assigned_items:
            if oi.book_item:
                assigned_map.setdefault(oi.book_item.isbn, []).append(str(oi.book_item.id))

        # Build books list
        books_out = []
        for req in requested_items:
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

    @staticmethod
    async def accept_return(db: AsyncSession, order_id: UUID) -> dict:
        """Accept returned books from reader."""

        # Fetch order
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found",
            )

        # Validate order status
        if order.status != OrderStatus.RETURN_IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept return: order status is '{order.status}' (expected 'return_in_progress')",
            )

        # Find return shipment
        stmt = (
            select(LockerShipment)
            .where(LockerShipment.order_id == order_id, LockerShipment.mode == "return")
            .order_by(LockerShipment.created_at.desc())
        )
        result = await db.execute(stmt)
        return_shipment = result.unique().scalar_one_or_none()  # ✅ .unique()

        if not return_shipment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Return shipment not found",
            )

        # Validate shipment status
        if return_shipment.status != "placed_in_locker":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot accept return: shipment status is '{return_shipment.status}' (expected 'placed_in_locker')",
            )

        # Update shipment status
        return_shipment.status = "completed"

        # Update order status
        order.status = OrderStatus.RETURNED
        order.updated_at = datetime.utcnow()

        # Fetch OrderItems
        stmt = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .options(selectinload(OrderItem.book_item))
        )
        result = await db.execute(stmt)
        order_items = result.unique().scalars().all()  # ✅ .unique()

        # ✅ POPRAWKA: returned_at = max(due_date) aby spełnić constraint
        returned_at = max([oi.due_date for oi in order_items if oi.due_date] or [datetime.utcnow()])

        for order_item in order_items:
            order_item.returned_at = returned_at  # ✅ Teraz OK z constraintem

            # Release BookItem
            if order_item.book_item:
                order_item.book_item.is_available = True
                order_item.book_item.current_location = BookLocation.LIBRARY
                db.add(order_item.book_item)

        await db.commit()

        return {"message": "Return accepted successfully - books are back in library"}
