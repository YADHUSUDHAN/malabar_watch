"""Unit tests for ingestion metrics and mathematical calculation functions."""

import math
from datetime import datetime

import pytest

from malabar_watch.ingestion.metrics import (
    calculate_antecedent_precipitation_index,
    calculate_rolling_total,
    compute_derived_metrics,
    sanitize_precipitation_series,
)
from malabar_watch.ingestion.models import HourlyPrecipitationData


@pytest.mark.unit
def test_sanitize_precipitation_series() -> None:
    """Ensure nulls, NaNs, and negative numbers are cleanly converted to 0.0."""
    raw = [10.5, None, -3.2, float("nan"), 0.0, 25.8]
    sanitized = sanitize_precipitation_series(raw)  # type: ignore[arg-type]
    assert sanitized == [10.5, 0.0, 0.0, 0.0, 0.0, 25.8]


@pytest.mark.unit
def test_calculate_rolling_total_standard() -> None:
    """Verify rolling cumulative calculation over 1h, 24h, 48h, 72h."""
    # 72 hours of 1.0mm rain per hour
    series = [1.0] * 72

    assert calculate_rolling_total(series, hours=1) == 1.0
    assert calculate_rolling_total(series, hours=24) == 24.0
    assert calculate_rolling_total(series, hours=48) == 48.0
    assert calculate_rolling_total(series, hours=72) == 72.0


@pytest.mark.unit
def test_calculate_rolling_total_edge_cases() -> None:
    """Verify empty and short window handling."""
    assert calculate_rolling_total([], hours=24) == 0.0
    assert calculate_rolling_total([5.0, 10.0], hours=24) == 15.0
    assert calculate_rolling_total([5.0, 10.0], hours=0) == 0.0
    assert calculate_rolling_total([5.0, 10.0], hours=-5) == 0.0


@pytest.mark.unit
def test_antecedent_precipitation_index_decay() -> None:
    """Verify recursive API decay formula: API_t = P_t + alpha * API_{t-1}."""
    # 3 days (72 hours total):
    # Day 1 (hours 0-23): 50mm total
    # Day 2 (hours 24-47): 20mm total
    # Day 3 (hours 48-71): 0mm total
    day1 = [50.0 / 24.0] * 24
    day2 = [20.0 / 24.0] * 24
    day3 = [0.0] * 24
    series = day1 + day2 + day3

    # Day 1: API = 50.0
    # Day 2: API = 20.0 + 0.85 * 50.0 = 20.0 + 42.5 = 62.5
    # Day 3: API = 0.0 + 0.85 * 62.5 = 53.125 -> 53.12
    api = calculate_antecedent_precipitation_index(series, alpha=0.85)
    assert math.isclose(api, 53.12, abs_tol=0.05)


@pytest.mark.unit
def test_antecedent_precipitation_index_zero_and_empty() -> None:
    """Verify API gracefully returns 0.0 on zero rain or empty series."""
    assert calculate_antecedent_precipitation_index([]) == 0.0
    assert calculate_antecedent_precipitation_index([0.0] * 72) == 0.0


@pytest.mark.unit
def test_compute_derived_metrics() -> None:
    """Verify end-to-end transformation into PrecipitationMetrics model."""
    now = datetime(2026, 9, 6, 12, 0)
    timestamps = [now] * 72
    precip = [2.0] * 72  # 2mm each hour

    hourly_data = HourlyPrecipitationData(timestamps=timestamps, precipitation=precip)
    metrics = compute_derived_metrics("wayanad", hourly_data, alpha=0.85)

    assert metrics.district_id == "wayanad"
    assert metrics.timestamp == now
    assert metrics.rainfall_1h == 2.0
    assert metrics.rainfall_24h == 48.0
    assert metrics.rainfall_48h == 96.0
    assert metrics.rainfall_72h == 144.0
    assert metrics.antecedent_index > 0.0
