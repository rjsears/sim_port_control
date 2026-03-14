"""
Tests for health check endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint returns OK."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_api_root(client):
    """Test API root endpoint."""
    response = await client.get("/api")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "SimPortControl API"
    assert "version" in data
