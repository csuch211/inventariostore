"""
End-to-end tests for the FastAPI REST API.

These tests use httpx to make real HTTP requests to the running application,
ensuring that the entire stack (API layer, controllers, repositories) is
working correctly together.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from api.rest import app


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """Verify that the /health endpoint is available and returns a 200 OK status."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_products_unauthenticated_fails():
    """Verify that accessing a protected endpoint without authentication fails with 401."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/productos")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_products_authenticated_succeeds(ctrl):
    """
    Verify that accessing a protected endpoint with valid authentication
    (via X-User header for testing) succeeds and returns product data.
    """
    # Arrange: Ensure there is at least one product in the test database
    await ctrl.crear_producto(codigo="API-TEST-01", nombre="Producto API", precio=99.99)

    # Act: Make an authenticated request
    async with AsyncClient(app=app, base_url="http://test") as client:
        headers = {"X-User": "admin"}  # Simulate an authenticated admin user
        response = await client.get("/productos", headers=headers)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "codigo" in data[0]
    assert data[0]["codigo"] == "API-TEST-01"