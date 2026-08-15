"""Data ingestion package for fetching and parsing Open-Meteo rainfall metrics."""

from typing import Any


class OpenMeteoClient:
    """Client for retrieving weather data from Open-Meteo API."""

    def __init__(self, base_url: str = "https://api.open-meteo.com/v1/forecast") -> None:
        self.base_url = base_url

    async def fetch_hourly_precipitation(
        self, latitude: float, longitude: float, past_days: int = 3
    ) -> dict[str, Any]:
        """Placeholder method for fetching hourly precipitation metrics."""
        return {
            "latitude": latitude,
            "longitude": longitude,
            "past_days": past_days,
            "status": "not_implemented",
        }
