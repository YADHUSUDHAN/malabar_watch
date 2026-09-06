import logging
from datetime import datetime
from typing import Any

import backoff
import httpx

from malabar_watch.config import settings
from malabar_watch.ingestion.models import HourlyPrecipitationData

logger = logging.getLogger(__name__)


class OpenMeteoClient:
    """Resilient asynchronous client for Open-Meteo Weather API."""

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url or settings.OPEN_METEO_BASE_URL
        self.timeout = timeout_seconds
        self._external_client = http_client

    @backoff.on_exception(
        backoff.expo,
        (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError),
        max_tries=3,
        giveup=lambda e: isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500,
    )
    async def fetch_hourly_precipitation(
        self,
        latitude: float,
        longitude: float,
        past_days: int = 3,
        forecast_days: int = 1,
    ) -> HourlyPrecipitationData:
        """Fetches hourly precipitation from Open-Meteo for given coordinates.

        Args:
            latitude: Latitude of target micro-zone.
            longitude: Longitude of target micro-zone.
            past_days: Trailing days to retrieve (default: 3 for 72h window).
            forecast_days: Ahead days to retrieve (default: 1).

        Returns:
            HourlyPrecipitationData containing parsed timestamps and rain amounts.

        Raises:
            httpx.HTTPError: If network or server response fails after retries.
            ValueError: If Open-Meteo payload is missing required hourly fields.
        """
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "precipitation,rain,showers",
            "timezone": "Asia/Kolkata",
            "past_days": past_days,
            "forecast_days": forecast_days,
        }

        logger.debug(
            "Fetching precipitation from Open-Meteo: lat=%.4f, lon=%.4f, past_days=%d",
            latitude,
            longitude,
            past_days,
        )

        if self._external_client is not None:
            response = await self._external_client.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()
            payload = response.json()
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params, timeout=self.timeout)
                response.raise_for_status()
                payload = response.json()

        parsed = self._parse_payload(payload)
        logger.debug(
            "Parsed %d hourly records from Open-Meteo for (%.4f, %.4f)",
            len(parsed.timestamps),
            latitude,
            longitude,
        )
        return parsed

    def _parse_payload(self, payload: dict[str, Any]) -> HourlyPrecipitationData:
        """Parses and validates Open-Meteo JSON response into HourlyPrecipitationData."""
        hourly = payload.get("hourly")
        if not hourly or not isinstance(hourly, dict):
            raise ValueError("Malformed Open-Meteo payload: missing 'hourly' object")

        raw_times = hourly.get("time", [])
        raw_precip = hourly.get("precipitation", [])

        if len(raw_times) != len(raw_precip):
            raise ValueError(
                "Mismatched array lengths in Open-Meteo response: "
                f"{len(raw_times)} times vs {len(raw_precip)} precipitation values"
            )

        parsed_times: list[datetime] = []
        for t_str in raw_times:
            # ISO formatted timestamp (e.g. 2026-09-06T12:00)
            parsed_times.append(datetime.fromisoformat(t_str))

        parsed_precip: list[float] = [float(p) if p is not None else 0.0 for p in raw_precip]

        return HourlyPrecipitationData(
            timestamps=parsed_times,
            precipitation=parsed_precip,
        )
