"""Mathematical calculation functions for derived rainfall metrics and soil saturation indices."""

import math
from collections.abc import Sequence
from datetime import datetime

from malabar_watch.config import now_ist
from malabar_watch.ingestion.models import HourlyPrecipitationData, PrecipitationMetrics


def sanitize_precipitation_series(values: Sequence[float | None]) -> list[float]:
    """Sanitizes raw precipitation values by converting nulls, NaNs, and negative values to 0.0."""
    sanitized: list[float] = []
    for val in values:
        if val is None or math.isnan(val) or val < 0:
            sanitized.append(0.0)
        else:
            sanitized.append(float(val))
    return sanitized


def calculate_rolling_total(precipitation: list[float], hours: int) -> float:
    """Calculates trailing cumulative precipitation over a specified hourly window.

    Args:
        precipitation: Time-ordered list of hourly precipitation (oldest to newest).
        hours: Window size in hours (e.g. 1, 24, 48, 72).

    Returns:
        Sum of precipitation within the window, rounded to 2 decimal places.
    """
    if not precipitation or hours <= 0:
        return 0.0

    window = precipitation[-hours:] if len(precipitation) >= hours else precipitation
    return round(float(sum(window)), 2)


def calculate_antecedent_precipitation_index(
    hourly_series: list[float],
    alpha: float = 0.85,
) -> float:
    """Computes the Antecedent Precipitation Index (API) with daily soil moisture decay.

    Formula:
        API_t = P_t + alpha * API_{t-1}
        Where P_t is precipitation on day t, and alpha is daily decay (default: 0.85).

    The hourly time series is split into sequential 24-hour day chunks, and the recursive
    API decay is computed up to the current day.

    Args:
        hourly_series: Time-ordered hourly precipitation series (oldest to newest).
        alpha: Soil drainage decay factor representing laterite soil drainage (0.0 to 1.0).

    Returns:
        Antecedent Precipitation Index value rounded to 2 decimal places.
    """
    if not hourly_series:
        return 0.0

    sanitized = sanitize_precipitation_series(hourly_series)
    if not sanitized:
        return 0.0

    # Group into 24-hour daily chunks
    daily_chunks: list[float] = []
    chunk_size = 24

    for i in range(0, len(sanitized), chunk_size):
        chunk = sanitized[i : i + chunk_size]
        daily_chunks.append(sum(chunk))

    # Apply recursive decay formula
    api = 0.0
    for day_precip in daily_chunks:
        api = day_precip + (alpha * api)

    return round(float(api), 2)


def compute_derived_metrics(
    district_id: str,
    hourly_data: HourlyPrecipitationData,
    alpha: float = 0.85,
    reference_time: datetime | None = None,
) -> PrecipitationMetrics:
    """Computes rolling totals and antecedent precipitation index from raw hourly data.

    Args:
        district_id: District identifier.
        hourly_data: Raw precipitation timeseries from Open-Meteo.
        alpha: Decay factor for Antecedent Precipitation Index.
        reference_time: Optional cutoff timestamp (defaults to current Indian Standard Time).

    Returns:
        Structured PrecipitationMetrics ready for persistence and risk assessment.
    """
    cutoff = reference_time or now_ist()

    # Filter out future forecast timestamps if present
    if hourly_data.timestamps and any(t > cutoff for t in hourly_data.timestamps):
        valid_pairs = [
            (t, p)
            for t, p in zip(hourly_data.timestamps, hourly_data.precipitation, strict=False)
            if t <= cutoff
        ]
        if valid_pairs:
            filtered_timestamps = [t for t, _ in valid_pairs]
            filtered_precip = [p for _, p in valid_pairs]
        else:
            filtered_timestamps = hourly_data.timestamps[:1]
            filtered_precip = hourly_data.precipitation[:1]
    else:
        filtered_timestamps = hourly_data.timestamps
        filtered_precip = hourly_data.precipitation

    sanitized_precip = sanitize_precipitation_series(filtered_precip)
    latest_timestamp = filtered_timestamps[-1] if filtered_timestamps else cutoff

    r1h = calculate_rolling_total(sanitized_precip, hours=1)
    r24h = calculate_rolling_total(sanitized_precip, hours=24)
    r48h = calculate_rolling_total(sanitized_precip, hours=48)
    r72h = calculate_rolling_total(sanitized_precip, hours=72)
    api = calculate_antecedent_precipitation_index(sanitized_precip, alpha=alpha)

    return PrecipitationMetrics(
        district_id=district_id,
        timestamp=latest_timestamp,
        rainfall_1h=r1h,
        rainfall_24h=r24h,
        rainfall_48h=r48h,
        rainfall_72h=r72h,
        antecedent_index=api,
    )
