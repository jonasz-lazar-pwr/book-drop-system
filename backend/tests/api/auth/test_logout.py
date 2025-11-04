# === tests/api/auth/test_logout.py ===

import pytest

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_returns_static_message(client: AsyncClient):
    """Test that /auth/logout returns a static success message."""
    response = await client.post("/auth/logout")
    assert response.status_code == 200
    assert response.json() == {"detail": "Logout successful. Tokens must be deleted client-side."}
