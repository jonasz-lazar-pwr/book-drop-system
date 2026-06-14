# tests/api/lockers/test_get_lockers.py

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Locker


@pytest.mark.asyncio
async def test_get_lockers_without_geolocation(client: AsyncClient, db_session: AsyncSession):
    """Return all lockers sorted alphabetically by city."""
    locker1 = Locker(
        locker_code="WRO-001",
        street="Street A",
        city="Wroclaw",
        postal_code="50-001",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    locker2 = Locker(
        locker_code="KRK-001",
        street="Street B",
        city="Krakow",
        postal_code="30-001",
        location="SRID=4326;POINT(19.9450 50.0647)",
    )
    db_session.add_all([locker1, locker2])
    await db_session.commit()

    res = await client.get("/api/lockers")

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    assert data[0]["locker_code"] in ["WRO-001", "KRK-001"]


@pytest.mark.asyncio
async def test_get_lockers_with_geolocation(client: AsyncClient, db_session: AsyncSession):
    """Return lockers sorted by distance when lat/lng provided."""
    # Wroclaw center
    locker1 = Locker(
        locker_code="WRO-001",
        street="Near Center",
        city="Wroclaw",
        postal_code="50-001",
        location="SRID=4326;POINT(17.0385 51.1079)",
    )
    # Far from Wroclaw
    locker2 = Locker(
        locker_code="GDA-001",
        street="Far Away",
        city="Gdansk",
        postal_code="80-001",
        location="SRID=4326;POINT(18.6466 54.3520)",
    )
    db_session.add_all([locker1, locker2])
    await db_session.commit()

    # Search from Wroclaw center
    res = await client.get("/api/lockers?lat=51.1079&lng=17.0385&limit=10")

    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 2
    # First result should be WRO-001 (closest)
    assert data[0]["locker_code"] == "WRO-001"


@pytest.mark.asyncio
async def test_get_lockers_with_limit(client: AsyncClient, db_session: AsyncSession):
    """Respect limit parameter."""
    for i in range(15):
        locker = Locker(
            locker_code=f"TEST-{i:03d}",
            street=f"Street {i}",
            city="TestCity",
            postal_code=f"00-{i:03d}",
            location=f"SRID=4326;POINT({17 + i * 0.01} {51 + i * 0.01})",
        )
        db_session.add(locker)
    await db_session.commit()

    res = await client.get("/api/lockers?limit=5")

    assert res.status_code == 200
    data = res.json()
    assert len(data) == 5


@pytest.mark.asyncio
async def test_get_lockers_invalid_coordinates(client: AsyncClient):
    """Return 422 when invalid lat/lng provided."""
    res = await client.get("/api/lockers?lat=999&lng=17.0385")
    assert res.status_code == 422
