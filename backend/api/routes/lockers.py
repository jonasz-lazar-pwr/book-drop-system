# api/routes/lockers.py

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from geoalchemy2.functions import ST_Distance, ST_MakePoint
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.deps import get_db
from models import Locker
from schemas.order import LockerResponse

router = APIRouter(tags=["Lockers"])


def _parse_location(location) -> tuple[float, float]:
    """
    Parse PostGIS POINT to (latitude, longitude).
    Handles both WKBElement (from DB) and string (from tests).
    """
    if isinstance(location, str):
        # String format: "SRID=4326;POINT(17.0385 51.1079)"
        try:
            point_str = location.split("POINT(")[1].replace(")", "").strip()
            lng, lat = point_str.split()
            return float(lat), float(lng)
        except (IndexError, ValueError) as err:
            raise ValueError(f"Invalid POINT string format: {location}") from err

    # WKBElement from GeoAlchemy2
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

        raise ValueError(
            f"Cannot parse location: unsupported type {type(location).__name__}. "
            f"Original error: {err}"
        ) from err


@router.get("", response_model=List[LockerResponse])
async def get_lockers(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    ✅ GET /api/lockers

    Zwraca listę książkomatów.

    Jeśli podane lat/lng → sortuje po odległości (PostGIS).
    Jeśli nie → sortuje alfabetycznie po mieście.
    """
    stmt = select(Locker)

    # Geolokalizacja (PostGIS)
    if lat is not None and lng is not None:
        user_point = ST_MakePoint(lng, lat)
        stmt = stmt.order_by(ST_Distance(Locker.location, user_point))
    else:
        stmt = stmt.order_by(Locker.city, Locker.street)

    stmt = stmt.limit(limit)
    result = await db.execute(stmt)
    lockers = result.scalars().all()

    # Convert ORM objects to LockerResponse with parsed lat/lng
    response = []
    for locker in lockers:
        latitude, longitude = _parse_location(locker.location)
        response.append(
            LockerResponse(
                id=locker.id,
                locker_code=locker.locker_code,
                street=locker.street,
                city=locker.city,
                postal_code=locker.postal_code,
                latitude=latitude,
                longitude=longitude,
            )
        )

    return response
