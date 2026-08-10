import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_request_id_header_is_propagated(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/live", headers={"X-Request-ID": "test-req-id"})

    assert response.headers["X-Request-ID"] == "test-req-id"
