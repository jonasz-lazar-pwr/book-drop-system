# === tests/api/checkout/test_list_lockers.py ===

import pytest

from geoalchemy2.shape import from_shape
from httpx import AsyncClient
from shapely.geometry import Point
from sqlalchemy.ext.asyncio import AsyncSession

from models import Locker


@pytest.mark.asyncio
async def test_list_lockers_returns_all(client: AsyncClient, db_session: AsyncSession):
    """Return all lockers when no filters are provided."""
    lockers = [
        Locker(
            locker_code="LCK-001",
            street="Main St 1",
            city="Wrocław",
            postal_code="50-001",
            location=from_shape(Point(17.0385, 51.1079), srid=4326),
        ),
        Locker(
            locker_code="LCK-002",
            street="Market Sq 2",
            city="Kraków",
            postal_code="31-001",
            location=from_shape(Point(19.9409, 50.0614), srid=4326),
        ),
    ]
    db_session.add_all(lockers)
    await db_session.commit()

    res = await client.get("/api/checkout/lockers")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert all("locker_code" in locker for locker in data)
    assert all("lat" in locker and "lon" in locker for locker in data)
    assert all(locker["distance_km"] is None for locker in data)


@pytest.mark.asyncio
async def test_list_lockers_filter_by_city(client: AsyncClient, db_session: AsyncSession):
    """Filter lockers by city name (case-insensitive partial match)."""
    db_session.add_all(
        [
            Locker(
                locker_code="LCK-A",
                street="Street 1",
                city="Warszawa",
                postal_code="00-001",
                location=from_shape(Point(21.0122, 52.2297), srid=4326),
            ),
            Locker(
                locker_code="LCK-B",
                street="Street 2",
                city="Gdańsk",
                postal_code="80-001",
                location=from_shape(Point(18.6466, 54.3520), srid=4326),
            ),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/checkout/lockers", params={"city": "warsz"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["city"].lower() == "warszawa"


@pytest.mark.asyncio
async def test_list_lockers_filter_by_street(client: AsyncClient, db_session: AsyncSession):
    """Ignore deprecated street filter and return all lockers."""
    db_session.add_all(
        [
            Locker(
                locker_code="LCK-STR-1",
                street="Józefa Piłsudskiego 105",
                city="Wrocław",
                postal_code="50-046",
                location=from_shape(Point(17.0385, 51.1079), srid=4326),
            ),
            Locker(
                locker_code="LCK-STR-2",
                street="Rynek 1",
                city="Wrocław",
                postal_code="50-438",
                location=from_shape(Point(17.035, 51.110), srid=4326),
            ),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/checkout/lockers", params={"street": "piłsud"})
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert any("Piłsudskiego" in locker["street"] for locker in data)


@pytest.mark.asyncio
async def test_list_lockers_filter_by_postal_code(client: AsyncClient, db_session: AsyncSession):
    """Return locker matching exact postal code."""
    db_session.add_all(
        [
            Locker(
                locker_code="LCK-100",
                street="Street 10",
                city="Poznań",
                postal_code="60-001",
                location=from_shape(Point(16.9252, 52.4064), srid=4326),
            ),
            Locker(
                locker_code="LCK-200",
                street="Street 20",
                city="Łódź",
                postal_code="90-001",
                location=from_shape(Point(19.4801, 51.7592), srid=4326),
            ),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/checkout/lockers", params={"postal_code": "60-001"})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["postal_code"] == "60-001"


@pytest.mark.asyncio
async def test_list_lockers_combined_filters(client: AsyncClient, db_session: AsyncSession):
    """Support combining city and postal_code filters."""
    db_session.add_all(
        [
            Locker(
                locker_code="LCK-WRO-1",
                street="Main 10",
                city="Wrocław",
                postal_code="50-001",
                location=from_shape(Point(17.0385, 51.1079), srid=4326),
            ),
            Locker(
                locker_code="LCK-WRO-2",
                street="Rynek 5",
                city="Wrocław",
                postal_code="50-046",
                location=from_shape(Point(17.035, 51.110), srid=4326),
            ),
        ]
    )
    await db_session.commit()

    res = await client.get(
        "/api/checkout/lockers", params={"city": "wroc", "postal_code": "50-046"}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["postal_code"] == "50-046"
    assert data[0]["city"].lower() == "wrocław"


@pytest.mark.asyncio
async def test_list_lockers_filter_by_radius(client: AsyncClient, db_session: AsyncSession):
    """Return only lockers within given radius."""
    wroclaw = Locker(
        locker_code="LCK-WRO",
        street="Rynek 1",
        city="Wrocław",
        postal_code="50-001",
        location=from_shape(Point(17.0385, 51.1079), srid=4326),
    )
    krakow = Locker(
        locker_code="LCK-KRK",
        street="Rynek Główny 2",
        city="Kraków",
        postal_code="31-001",
        location=from_shape(Point(19.9409, 50.0614), srid=4326),
    )
    db_session.add_all([wroclaw, krakow])
    await db_session.commit()

    res = await client.get(
        "/api/checkout/lockers",
        params={"lat": 51.1079, "lon": 17.0385, "radius": 150},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["locker_code"] == "LCK-WRO"
    assert data[0]["distance_km"] == pytest.approx(0.0, abs=0.05)


@pytest.mark.asyncio
async def test_list_lockers_returns_empty_if_no_results(
    client: AsyncClient, db_session: AsyncSession
):
    """Return empty list if no lockers match filters."""
    db_session.add(
        Locker(
            locker_code="LCK-999",
            street="Unknown 9",
            city="Rzeszów",
            postal_code="35-001",
            location=from_shape(Point(22.0, 50.0), srid=4326),
        )
    )
    await db_session.commit()

    res = await client.get("/api/checkout/lockers", params={"city": "NonexistentCity"})
    assert res.status_code == 200
    data = res.json()
    assert data == []


@pytest.mark.asyncio
async def test_list_lockers_invalid_geo_params(client: AsyncClient):
    """Return 422 if radius is provided without lat/lon."""
    res = await client.get("/api/checkout/lockers", params={"radius": 10})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_list_lockers_limit_results(client: AsyncClient, db_session: AsyncSession):
    """Limit results to N when limit parameter is set."""
    for i in range(30):
        db_session.add(
            Locker(
                locker_code=f"LCK-{i:03d}",
                street=f"Street {i}",
                city="Wrocław",
                postal_code=f"50-{i:03d}",
                location=from_shape(Point(17.0 + i * 0.001, 51.1), srid=4326),
            )
        )
    await db_session.commit()

    res = await client.get("/api/checkout/lockers", params={"city": "wroc", "limit": 20})
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 20
