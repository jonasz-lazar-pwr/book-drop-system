# repositories/order_repository.py

import secrets
import string

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import (
    BookItem,
    Locker,
    LockerBox,
    LockerShipment,
    Order,
    OrderItem,
)
from schemas.order import (
    LockerResponse,
    LockerShipmentResponse,
    OrderItemResponse,
    OrderResponse,
)


class OrderRepository:
    """Repository for managing book orders and returns."""

    # ============================================
    # HELPER: Generate pickup code
    # ============================================
    @staticmethod
    def _generate_pickup_code(length: int = 8) -> str:
        """Generate random alphanumeric pickup code (uppercase, no confusing chars)."""
        chars = string.ascii_uppercase + string.digits
        # Remove confusing characters: O, 0, I, 1
        chars = chars.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
        return "".join(secrets.choice(chars) for _ in range(length))

    # ============================================
    # HELPER: Parse PostGIS POINT
    # ============================================
    @staticmethod
    def _parse_point(location) -> tuple[float, float]:
        """
        Parse PostGIS POINT to (latitude, longitude).
        Handles both WKBElement (from DB) and string (from tests).

        Args:
            location: Either WKBElement from GeoAlchemy2 or string "SRID=4326;POINT(lng lat)"

        Returns:
            Tuple of (latitude, longitude)

        Raises:
            ValueError: If location format is not recognized
        """
        # Case 1: String format from tests
        if isinstance(location, str):
            # Format: "SRID=4326;POINT(17.0385 51.1079)"
            try:
                point_str = location.split("POINT(")[1].replace(")", "").strip()
                lng, lat = point_str.split()
                return float(lat), float(lng)
            except (IndexError, ValueError) as err:
                raise ValueError(f"Invalid POINT string format: {location}") from err

        # Case 2: WKBElement from GeoAlchemy2 (real DB query)
        try:
            from geoalchemy2.shape import to_shape  # noqa: PLC0415

            point = to_shape(location)
            return point.y, point.x  # (latitude, longitude)
        except (ImportError, AttributeError, TypeError) as err:
            # Fallback: try .desc attribute
            if hasattr(location, "desc"):
                try:
                    point_str = location.desc.split("(")[1].replace(")", "").strip()
                    lng, lat = point_str.split()
                    return float(lat), float(lng)
                except (IndexError, ValueError, AttributeError) as desc_err:
                    raise ValueError(f"Cannot parse location.desc: {location}") from desc_err

            # No fallback available
            raise ValueError(
                f"Cannot parse location: unsupported type {type(location).__name__}. "
                f"Original error: {err}"
            ) from err

    # ============================================
    # HELPER: Build OrderResponse from ORM object
    # ============================================
    @staticmethod
    def _build_order_response(order: Order) -> OrderResponse:
        """
        Convert SQLAlchemy Order model to Pydantic OrderResponse.
        Includes items with book details and shipment with locker info.
        """
        # Build order items (with book details from BookItem → Book)
        items = []
        for oi in order.items:
            book = oi.book_item.book if oi.book_item else None
            items.append(
                OrderItemResponse(
                    id=oi.id,
                    order_id=oi.order_id,
                    book_item_id=oi.book_item_id,
                    isbn=book.isbn if book else "Unknown",
                    title=book.title if book else "Unknown",
                    authors=book.authors if book else "Unknown",
                    publisher=book.publisher if book else None,
                    thumbnail=book.thumbnail if book else None,
                    due_date=oi.due_date,
                    returned_at=oi.returned_at,
                )
            )

        # Build shipment (with locker details)
        shipment = None
        if order.shipments:
            # Get the most recent shipment (for orders with multiple shipments)
            latest_shipment = max(order.shipments, key=lambda s: s.created_at)

            # Get locker from locker_box
            locker_box = (
                latest_shipment.locker_box if hasattr(latest_shipment, "locker_box") else None
            )
            locker = locker_box.locker if locker_box else None

            if locker:
                # Parse location (handles both string and WKBElement)
                lat, lng = OrderRepository._parse_point(locker.location)

                shipment = LockerShipmentResponse(
                    id=latest_shipment.id,
                    order_id=latest_shipment.order_id,
                    locker=LockerResponse(
                        id=locker.id,
                        locker_code=locker.locker_code,
                        street=locker.street,
                        city=locker.city,
                        postal_code=locker.postal_code,
                        latitude=lat,
                        longitude=lng,
                    ),
                    mode=latest_shipment.mode,
                    status=latest_shipment.status,
                    pickup_code=latest_shipment.pickup_code,
                    placed_at=latest_shipment.placed_at,
                    created_at=latest_shipment.created_at,
                )

        return OrderResponse(
            id=order.id,
            reader_id=order.reader_id,
            status=order.status,
            created_at=order.created_at,
            updated_at=order.updated_at,
            items=items,
            shipment=shipment,
        )

    # ============================================
    # GET: Lista zamówień użytkownika
    # ============================================
    @staticmethod
    async def get_user_orders(
        db: AsyncSession,
        user_id: UUID,
        status_filter: Optional[str] = None,
    ) -> List[OrderResponse]:
        """
        Zwraca listę wszystkich zamówień użytkownika (aktywne + historia).

        Args:
            db: Database session
            user_id: ID użytkownika
            status_filter: Opcjonalny filtr po statusie zamówienia

        Returns:
            Lista OrderResponse posortowana od najnowszych
        """
        stmt = (
            select(Order)
            .where(Order.reader_id == user_id)
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.book_item)
                .selectinload(BookItem.book),
                selectinload(Order.shipments)
                .selectinload(LockerShipment.locker_box)
                .selectinload(LockerBox.locker),
            )
            .order_by(Order.created_at.desc())
        )

        # Apply status filter if provided
        if status_filter:
            stmt = stmt.where(Order.status == status_filter)

        result = await db.execute(stmt)
        orders = result.scalars().all()

        return [OrderRepository._build_order_response(order) for order in orders]

    # ============================================
    # GET: Szczegóły jednego zamówienia
    # ============================================
    @staticmethod
    async def get_order_by_id(
        db: AsyncSession,
        order_id: UUID,
        user_id: UUID,
    ) -> Optional[OrderResponse]:
        """
        Zwraca szczegóły konkretnego zamówienia.

        Args:
            db: Database session
            order_id: ID zamówienia
            user_id: ID użytkownika (dla walidacji dostępu)

        Returns:
            OrderResponse lub None jeśli nie znaleziono

        Raises:
            HTTPException 403: Jeśli zamówienie nie należy do użytkownika
        """
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items)
                .selectinload(OrderItem.book_item)
                .selectinload(BookItem.book),
                selectinload(Order.shipments)
                .selectinload(LockerShipment.locker_box)
                .selectinload(LockerBox.locker),
            )
        )

        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            return None

        # Verify ownership
        if str(order.reader_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Order does not belong to you",
            )

        return OrderRepository._build_order_response(order)

    # ============================================
    # POST: Potwierdzenie odbioru
    # ============================================
    @staticmethod
    async def confirm_pickup(
        db: AsyncSession,
        order_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Potwierdza odbiór książek z książkomatu.

        Flow:
        1. Walidacja: czy order należy do usera
        2. Walidacja: czy status = 'ready_for_pickup'
        3. Zmiana statusu order: ready_for_pickup → picked_up
        4. Zmiana statusu shipment: placed_in_locker → retrieved_by_user
        5. Ustawienie due_date dla każdego OrderItem (np. +14 dni)

        Args:
            db: Database session
            order_id: ID zamówienia
            user_id: ID użytkownika

        Raises:
            HTTPException 404: Order not found
            HTTPException 403: Access denied
            HTTPException 400: Invalid order status
        """
        # Fetch order with relationships
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.shipments),
            )
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Verify ownership
        if str(order.reader_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Verify status
        if order.status != "ready_for_pickup":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm pickup: order status is '{order.status}' (expected 'ready_for_pickup')",
            )

        # Update order status
        order.status = "picked_up"
        order.updated_at = datetime.utcnow()

        # Update shipment status (delivery mode)
        for shipment in order.shipments:
            if shipment.mode == "delivery":
                shipment.status = "retrieved_by_user"

        # Set due_date for all items (14 days from now)
        due_date = datetime.utcnow() + timedelta(days=14)
        for item in order.items:
            if not item.due_date:
                item.due_date = due_date

        await db.commit()

    # ============================================
    # POST: Inicjacja zwrotu
    # ============================================
    @staticmethod
    async def initiate_return(
        db: AsyncSession,
        order_id: UUID,
        user_id: UUID,
        locker_id: UUID,
    ) -> LockerShipmentResponse:
        """
        Inicjuje zwrot książek.

        Flow:
        1. Walidacja: czy order należy do usera
        2. Walidacja: czy status = 'picked_up'
        3. Znajdź dostępną skrytkę w wybranym lockerze
        4. Stwórz nowy shipment typu 'return' z pickup_code
        5. Zmiana statusu order: picked_up → return_in_progress
        6. Zarezerwuj skrytkę (is_available = False)

        Args:
            db: Database session
            order_id: ID zamówienia
            user_id: ID użytkownika
            locker_id: ID książkomatu dla zwrotu

        Returns:
            LockerShipmentResponse z pickup_code

        Raises:
            HTTPException 404: Order/Locker not found
            HTTPException 403: Access denied
            HTTPException 400: Invalid status or no available boxes
        """
        # Fetch order
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.shipments))
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Verify ownership
        if str(order.reader_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Verify status
        if order.status != "picked_up":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot initiate return: order status is '{order.status}' (expected 'picked_up')",
            )

        # Find available box in selected locker
        stmt = (
            select(LockerBox)
            .where(
                and_(
                    LockerBox.locker_id == locker_id,
                    LockerBox.is_available.is_(True),
                )
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        box = result.scalar_one_or_none()

        if not box:
            raise HTTPException(
                status_code=400,
                detail="No available boxes in selected locker",
            )

        # Generate pickup code
        pickup_code = OrderRepository._generate_pickup_code()

        # Create return shipment (use "return" string, not enum)
        shipment = LockerShipment(
            order_id=order_id,
            locker_box_id=box.id,
            mode="return",  # ✅ string value
            status="created",  # ✅ string value
            pickup_code=pickup_code,
        )
        db.add(shipment)

        # Update order status
        order.status = "return_in_progress"
        order.updated_at = datetime.utcnow()

        # Reserve box
        box.is_available = False

        await db.commit()
        await db.refresh(shipment)

        # Fetch locker for response
        stmt = select(Locker).where(Locker.id == locker_id)
        result = await db.execute(stmt)
        locker = result.scalar_one()

        # Parse location (handles both string and WKBElement)
        lat, lng = OrderRepository._parse_point(locker.location)

        return LockerShipmentResponse(
            id=shipment.id,
            order_id=shipment.order_id,
            locker=LockerResponse(
                id=locker.id,
                locker_code=locker.locker_code,
                street=locker.street,
                city=locker.city,
                postal_code=locker.postal_code,
                latitude=lat,
                longitude=lng,
            ),
            mode=shipment.mode,
            status=shipment.status,
            pickup_code=shipment.pickup_code,
            placed_at=shipment.placed_at,
            created_at=shipment.created_at,
        )

    # ============================================
    # POST: Potwierdzenie zwrotu
    # ============================================
    @staticmethod
    async def confirm_return(
        db: AsyncSession,
        order_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Potwierdza umieszczenie książek w książkomacie (zwrot).

        Flow:
        1. Walidacja: czy order należy do usera
        2. Walidacja: czy status = 'return_in_progress'
        3. ✅ NOWE: Walidacja czy shipment nie został już potwierdzony
        4. Zmiana statusu shipment: created → placed_in_locker
        5. Ustawienie placed_at timestamp

        UWAGA: Status order zostanie zmieniony na 'returned' przez kuriera
        po odbiorze książek z książkomatu.

        Args:
            db: Database session
            order_id: ID zamówienia
            user_id: ID użytkownika

        Raises:
            HTTPException 404: Order/Shipment not found
            HTTPException 403: Access denied
            HTTPException 400: Invalid status or already confirmed
        """
        # Fetch order with shipments
        stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.shipments))
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        # Verify ownership
        if str(order.reader_id) != str(user_id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Verify order status
        if order.status != "return_in_progress":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm return: order status is '{order.status}' (expected 'return_in_progress')",
            )

        # Find return shipment (most recent one with mode='return')
        return_shipments = [s for s in order.shipments if s.mode == "return"]

        if not return_shipments:
            raise HTTPException(
                status_code=404,
                detail="Return shipment not found",
            )

        # Get the most recent return shipment
        return_shipment = max(return_shipments, key=lambda s: s.created_at)

        # ✅ NOWA WALIDACJA: Sprawdź czy już nie został potwierdzony
        if return_shipment.status == "placed_in_locker":
            raise HTTPException(
                status_code=400,
                detail="Return already confirmed - books are in locker waiting for courier pickup",
            )

        if return_shipment.status == "completed":
            raise HTTPException(
                status_code=400,
                detail="Return already completed - books have been collected by courier",
            )

        # ✅ DODATKOWA WALIDACJA: Tylko 'created' może być zmieniony na 'placed_in_locker'
        if return_shipment.status != "created":
            raise HTTPException(
                status_code=400,
                detail=f"Cannot confirm return: shipment status is '{return_shipment.status}' (expected 'created')",
            )

        # Update shipment status
        return_shipment.status = "placed_in_locker"
        return_shipment.placed_at = datetime.utcnow()

        # Update order timestamp (status stays 'return_in_progress' until courier collects)
        order.updated_at = datetime.utcnow()

        await db.commit()
