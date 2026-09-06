"""Data ingestion package for fetching and parsing Open-Meteo rainfall metrics."""

from malabar_watch.ingestion.client import OpenMeteoClient
from malabar_watch.ingestion.metrics import (
    calculate_antecedent_precipitation_index,
    calculate_rolling_total,
    compute_derived_metrics,
    sanitize_precipitation_series,
)
from malabar_watch.ingestion.models import (
    DEFAULT_TARGETS,
    DistrictTarget,
    HourlyPrecipitationData,
    PrecipitationMetrics,
)
from malabar_watch.ingestion.service import DataIngestionService

__all__ = [
    "DEFAULT_TARGETS",
    "DataIngestionService",
    "DistrictTarget",
    "HourlyPrecipitationData",
    "OpenMeteoClient",
    "PrecipitationMetrics",
    "calculate_antecedent_precipitation_index",
    "calculate_rolling_total",
    "compute_derived_metrics",
    "sanitize_precipitation_series",
]
