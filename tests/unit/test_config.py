"""Unit tests for configuration loading."""

import pytest

from malabar_watch.config import Settings


@pytest.mark.unit
def test_default_settings() -> None:
    """Verify default settings values."""
    config = Settings()
    assert config.ENVIRONMENT == "development"
    assert config.OPEN_METEO_BASE_URL == "https://api.open-meteo.com/v1/forecast"
    assert config.RAINFALL_EXTREME_THRESHOLD_24H == 204.4
