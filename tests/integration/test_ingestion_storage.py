"""Integration tests verifying DataIngestionService end-to-end with SQLite persistence."""

from datetime import datetime, timedelta
from typing import Any

import httpx
import pytest

from malabar_watch.ingestion.client import OpenMeteoClient
from malabar_watch.ingestion.models import DEFAULT_TARGETS
from malabar_watch.ingestion.service import DataIngestionService
from malabar_watch.storage import DatabaseManager


class MockTransport(httpx.AsyncBaseTransport):
    """Mock transport providing 72 hours of sample hourly data."""

    def __init__(self, base_rain: float = 2.0) -> None:
        self.base_rain = base_rain

    async def handle_async_request(self, _request: httpx.Request) -> httpx.Response:
        now = datetime(2026, 9, 6, 12, 0)
        times = [(now - timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(71, -1, -1)]
        precip = [self.base_rain] * 72
        payload: dict[str, Any] = {
            "latitude": 11.6084,
            "longitude": 76.0883,
            "timezone": "Asia/Kolkata",
            "hourly": {
                "time": times,
                "precipitation": precip,
            },
        }
        return httpx.Response(200, json=payload)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_ingestion_service_end_to_end() -> None:
    """Verify full ingestion workflow: client poll -> calculate metrics -> SQLite storage."""
    db_manager = DatabaseManager(db_path=":memory:")
    # Initialize in-memory schema
    conn = db_manager.get_connection()
    db_manager.initialize_schema(conn)

    async with httpx.AsyncClient(transport=MockTransport(base_rain=3.0)) as mock_client:
        client = OpenMeteoClient(http_client=mock_client)
        service = DataIngestionService(client=client, db_manager=db_manager)

        # Ingest for Wayanad
        wayanad_target = DEFAULT_TARGETS["wayanad"]
        metrics = await service.fetch_and_process_district(wayanad_target)

        assert metrics.district_id == "wayanad"
        assert metrics.rainfall_1h == 3.0
        assert metrics.rainfall_24h == 72.0
        assert metrics.rainfall_48h == 144.0
        assert metrics.rainfall_72h == 216.0
        assert metrics.antecedent_index > 0.0

        # Verify storage in SQLite
        row = db_manager.get_latest_observation("wayanad", conn=conn)
        assert row is not None
        assert row["district"] == "wayanad"
        assert row["precipitation_mm"] == 3.0
        assert row["rainfall_24h"] == 72.0
        assert row["rainfall_48h"] == 144.0
        assert row["rainfall_72h"] == 216.0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_ingestion_service_process_all_and_deduplication() -> None:
    """Verify fetch_and_process_all for all target districts and conflict deduplication."""
    db_manager = DatabaseManager(db_path=":memory:")
    conn = db_manager.get_connection()
    db_manager.initialize_schema(conn)

    async with httpx.AsyncClient(transport=MockTransport(base_rain=1.5)) as mock_client:
        client = OpenMeteoClient(http_client=mock_client)
        service = DataIngestionService(client=client, db_manager=db_manager)

        results = await service.fetch_and_process_all()
        assert "wayanad" in results
        assert "idukki" in results
        assert "kottayam" in results

        cursor = conn.execute("SELECT COUNT(*) FROM rainfall_observations;")
        assert cursor.fetchone()[0] == len(DEFAULT_TARGETS)

        # Running again with identical timestamp updates rather than inserting duplicates
        await service.fetch_and_process_all()
        cursor = conn.execute("SELECT COUNT(*) FROM rainfall_observations;")
        assert cursor.fetchone()[0] == len(DEFAULT_TARGETS)
