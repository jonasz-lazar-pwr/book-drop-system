# === repositories/checkout_repository.py ===

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Book,
    BookItem,
    Cart,
    CartItem,
    Locker,
    LockerBox,
    LockerShipment,
    Order,
    OrderRequestedItem,
)
from models.enums import CartStatus, OrderStatus, ShipmentMode, ShipmentStatus


class CheckoutRepository:
    """Handles async database operations for checkout and order creation."""

    @staticmethod
    async def get_summary(db: AsyncSession, user_id: str):
        """Fetch active cart summary with user and book details."""
        cart_q = await db.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        )
        cart = cart_q.scalar_one_or_none()
        if not cart:
            raise HTTPException(status_code=400, detail="No active cart found.")

        await db.refresh(cart, attribute_names=["user", "items"])

        items_q = await db.execute(
            select(Book.isbn, Book.title, Book.authors, CartItem.quantity)
            .join(CartItem, CartItem.isbn == Book.isbn)
            .where(CartItem.cart_id == cart.id)
        )
        items = items_q.all()

        if not items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        return {
            "user_id": user_id,
            "first_name": cart.user.first_name,
            "last_name": cart.user.last_name,
            "email": cart.user.email,
            "total_items": sum(i.quantity for i in items),
            "distinct_titles": len(items),
            "books": [
                {"isbn": i.isbn, "title": i.title, "authors": i.authors, "quantity": i.quantity}
                for i in items
            ],
        }

    @staticmethod
    async def list_lockers(
        db: AsyncSession,
        city: str | None = None,
        postal_code: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius: float | None = None,
        limit: int | None = 20,
    ):
        """List available lockers with optional filters (city, postal code, radius)."""
        params: dict[str, any] = {}
        calc_distance = lat is not None and lon is not None

        distance_expr = (
            "ST_Distance(location::geography, ST_MakePoint(:lon, :lat)::geography) / 1000"
            if calc_distance
            else "NULL"
        )

        base_sql_parts = [
            "SELECT",
            " id, locker_code, street, city, postal_code,",
            " ST_Y(location::geometry) AS lat,",
            " ST_X(location::geometry) AS lon,",
            f" {distance_expr} AS distance_km",
            " FROM locker",
            " WHERE 1=1",
        ]
        base_sql = " ".join(base_sql_parts)

        if city:
            base_sql += " AND city ILIKE :city"
            params["city"] = f"%{city}%"

        if postal_code:
            base_sql += " AND postal_code ILIKE :postal_code"
            params["postal_code"] = f"%{postal_code}%"

        if radius and not calc_distance:
            raise HTTPException(
                status_code=422,
                detail="Both lat and lon are required when using radius filter.",
            )

        if calc_distance:
            params.update({"lat": lat, "lon": lon})
            if radius:
                base_sql += " AND ST_DWithin(location::geography, ST_MakePoint(:lon, :lat)::geography, :radius_m)"
                params["radius_m"] = radius * 1000

        base_sql += " ORDER BY distance_km ASC NULLS LAST, city, locker_code"
        base_sql += " LIMIT :limit"
        params["limit"] = limit

        result = await db.execute(text(base_sql), params)
        rows = result.mappings().all()

        return [
            {
                "id": str(row["id"]),
                "locker_code": row["locker_code"],
                "street": row["street"],
                "city": row["city"],
                "postal_code": row["postal_code"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "distance_km": float(row["distance_km"])
                if row["distance_km"] is not None
                else None,
            }
            for row in rows
        ]

    @staticmethod
    async def submit_checkout(db: AsyncSession, user_id: str, locker_id: str):
        """Submit checkout using logical items (OrderRequestedItem)."""
        cart = await db.scalar(
            select(Cart).where(Cart.user_id == user_id, Cart.status == CartStatus.ACTIVE)
        )
        if not cart:
            raise HTTPException(status_code=400, detail="No active cart found.")

        await db.refresh(cart, attribute_names=["items"])
        if not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty.")

        unavailable = []
        for item in cart.items:
            available_count = await db.scalar(
                select(func.count(BookItem.id)).where(
                    BookItem.isbn == item.isbn,
                    BookItem.is_available.is_(True),
                )
            )
            if available_count < item.quantity:
                book = await db.scalar(select(Book).where(Book.isbn == item.isbn))
                unavailable.append(book.title if book else item.isbn)

        if unavailable:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot complete order — unavailable books: {', '.join(unavailable)}",
            )

        box = await db.scalar(
            select(LockerBox)
            .where(LockerBox.locker_id == locker_id, LockerBox.is_available.is_(True))
            .limit(1)
        )
        if not box:
            raise HTTPException(status_code=400, detail="No available locker boxes in this locker.")

        try:
            cart.status = CartStatus.SUBMITTED
            await db.flush()

            order = Order(reader_id=user_id, status=OrderStatus.NEW)
            db.add(order)
            await db.flush()

            for item in cart.items:
                requested = OrderRequestedItem(
                    order_id=order.id,
                    isbn=item.isbn,
                    quantity=item.quantity,
                )
                db.add(requested)

            box.is_available = False
            db.add(box)

            shipment = LockerShipment(
                order_id=order.id,
                locker_box_id=box.id,
                mode=ShipmentMode.DELIVERY,
                status=ShipmentStatus.CREATED,
            )
            db.add(shipment)

            new_cart = Cart(user_id=user_id, status=CartStatus.ACTIVE)
            db.add(new_cart)

            await db.commit()

        except Exception:
            await db.rollback()
            raise

        await db.refresh(shipment)
        locker = await db.scalar(select(Locker).where(Locker.id == locker_id))

        return {
            "order_id": str(order.id),
            "shipment_id": str(shipment.id),
            "pickup_code": shipment.pickup_code,
            "locker_code": locker.locker_code,
            "city": locker.city,
            "postal_code": locker.postal_code,
            "message": "Order successfully created and locker reserved.",
        }
