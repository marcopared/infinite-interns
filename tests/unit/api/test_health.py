import pytest

from infinite_interns.api.app import app, health


@pytest.mark.asyncio
async def test_health_route() -> None:
    assert any(getattr(route, "path", None) == "/api/health" for route in app.routes)
    assert await health() == {"status": "ok"}
