"""Unit tests for OpenMeteoClient HTTP interaction and payload parsing."""

from datetime import datetime
from typing import Any

import httpx
import pytest

from malabar_watch.ingestion.client import OpenMeteoClient


class MockTransport(httpx.AsyncBaseTransport):
    """Mock HTTP transport for testing without hitting live APIs."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return self.handler(request)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_hourly_precipitation_success() -> None:
    """Ensure valid Open-Meteo JSON payload parses into HourlyPrecipitationData."""

    def handler(request: httpx.Request) -> httpx.Response:
        assert "latitude=11.6084" in str(request.url)
        assert "longitude=76.0883" in str(request.url)
        payload = {
            "latitude": 11.6084,
            "longitude": 76.0883,
            "timezone": "Asia/Kolkata",
            "hourly": {
                "time": ["2026-09-06T10:00", "2026-09-06T11:00", "2026-09-06T12:00"],
                "precipitation": [0.0, 4.5, 12.0],
            },
        }
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=MockTransport(handler)) as mock_client:
        client = OpenMeteoClient(http_client=mock_client)
        data = await client.fetch_hourly_precipitation(11.6084, 76.0883)

        assert len(data.timestamps) == 3
        assert len(data.precipitation) == 3
        assert data.precipitation == [0.0, 4.5, 12.0]
        assert data.timestamps[-1] == datetime(2026, 9, 6, 12, 0)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_hourly_precipitation_missing_hourly_raises() -> None:
    """Ensure missing 'hourly' object raises ValueError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"latitude": 11.6084})

    async with httpx.AsyncClient(transport=MockTransport(handler)) as mock_client:
        client = OpenMeteoClient(http_client=mock_client)
        with pytest.raises(ValueError, match="missing 'hourly' object"):
            await client.fetch_hourly_precipitation(11.6084, 76.0883)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fetch_hourly_precipitation_mismatched_lengths_raises() -> None:
    """Ensure mismatched time and precipitation arrays raise ValueError."""

    def handler(_request: httpx.Request) -> httpx.Response:
        payload = {
            "hourly": {
                "time": ["2026-09-06T10:00", "2026-09-06T11:00"],
                "precipitation": [0.0],
            }
        }
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=MockTransport(handler)) as mock_client:
        client = OpenMeteoClient(http_client=mock_client)
        with pytest.raises(ValueError, match="Mismatched array lengths"):
            await client.fetch_hourly_precipitation(11.6084, 76.0883)
