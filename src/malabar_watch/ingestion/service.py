import logging
from collections.abc import Mapping

from malabar_watch.config import settings
from malabar_watch.ingestion.client import OpenMeteoClient
from malabar_watch.ingestion.metrics import compute_derived_metrics
from malabar_watch.ingestion.models import (
    DEFAULT_TARGETS,
    DistrictTarget,
    PrecipitationMetrics,
)
from malabar_watch.storage import DatabaseManager

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Orchestrates Open-Meteo polling, metric derivation, and SQLite persistence."""

    def __init__(
        self,
        client: OpenMeteoClient | None = None,
        db_manager: DatabaseManager | None = None,
        targets: Mapping[str, DistrictTarget] | None = None,
    ) -> None:
        self.client = client or OpenMeteoClient()
        self.db = db_manager or DatabaseManager()
        self.targets = targets or DEFAULT_TARGETS
        # Ensure schema tables are initialized
        self.db.initialize_schema()

    async def fetch_and_process_district(self, target: DistrictTarget) -> PrecipitationMetrics:
        """Fetches live weather data for a target, calculates metrics, and persists to SQLite.

        Args:
            target: DistrictTarget configuration with coordinates.

        Returns:
            PrecipitationMetrics containing all computed multi-window totals.
        """
        logger.info(
            "Polling weather data for target '%s' (%s, %.4f, %.4f)",
            target.district_id,
            target.name,
            target.latitude,
            target.longitude,
        )
        hourly_data = await self.client.fetch_hourly_precipitation(
            latitude=target.latitude,
            longitude=target.longitude,
            past_days=3,
            forecast_days=1,
        )

        metrics = compute_derived_metrics(
            district_id=target.district_id,
            hourly_data=hourly_data,
            alpha=settings.ANTECEDENT_PRECIPITATION_INDEX_ALPHA,
        )

        row_id = self.db.save_observation(metrics)
        logger.info(
            "Saved observation for '%s' (row_id=%d): 1h=%.1fmm, 24h=%.1fmm, API=%.1f",
            target.district_id,
            row_id,
            metrics.rainfall_1h,
            metrics.rainfall_24h,
            metrics.antecedent_index,
        )
        return metrics

    async def fetch_and_process_all(self) -> dict[str, PrecipitationMetrics]:
        """Polls all configured target micro-zones and saves observations to the database.

        Returns:
            Dictionary mapping district_id to calculated PrecipitationMetrics.
        """
        logger.info("Initiating weather ingestion across %d targets", len(self.targets))
        results: dict[str, PrecipitationMetrics] = {}
        for district_id, target in self.targets.items():
            results[district_id] = await self.fetch_and_process_district(target)
        logger.info("Successfully ingested weather data for all %d targets", len(results))
        return results
