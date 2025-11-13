# === tests/api/catalog/test_list_publishers.py ===

import pytest

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from models import Book


@pytest.mark.asyncio
async def test_list_publishers(client: AsyncClient, db_session: AsyncSession):
    """Should return a list of all unique publishers."""
    db_session.add_all(
        [
            Book(
                isbn="9781000000001",
                title="A",
                authors="X",
                publisher="Helion",
                published_date="2020-01-01",
            ),
            Book(
                isbn="9781000000002",
                title="B",
                authors="Y",
                publisher="O'Reilly",
                published_date="2021-01-01",
            ),
            Book(
                isbn="9781000000003",
                title="C",
                authors="Z",
                publisher="Helion",
                published_date="2022-01-01",
            ),
        ]
    )
    await db_session.commit()

    res = await client.get("/api/catalog/publishers")
    assert res.status_code == 200
    publishers = res.json()
    assert isinstance(publishers, list)
    assert "Helion" in publishers
    assert "O'Reilly" in publishers
    assert len(publishers) == 2
