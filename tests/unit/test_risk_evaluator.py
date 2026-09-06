"""Unit tests for deterministic RiskEvaluator and threshold precedence rules."""

from datetime import datetime

import pytest

from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.risk_engine import RiskLevel, evaluate_metrics
from malabar_watch.risk_engine.evaluator import RiskEvaluator


@pytest.mark.unit
@pytest.mark.parametrize(
    "r24, r48, api, expected_level",
    [
        # Zero rain and low rain baseline
        (0.0, 0.0, 0.0, RiskLevel.LOW),
        (25.0, 45.0, 35.0, RiskLevel.LOW),
        (49.9, 89.9, 59.9, RiskLevel.LOW),
        # Moderate triggers
        (50.0, 0.0, 0.0, RiskLevel.MODERATE),
        (0.0, 90.0, 0.0, RiskLevel.MODERATE),
        (0.0, 0.0, 60.0, RiskLevel.MODERATE),
        (75.0, 110.0, 80.0, RiskLevel.MODERATE),
        # High triggers
        (100.0, 0.0, 0.0, RiskLevel.HIGH),
        (0.0, 150.0, 0.0, RiskLevel.HIGH),
        (0.0, 0.0, 100.0, RiskLevel.HIGH),
        (160.0, 180.0, 120.0, RiskLevel.HIGH),
        # Severe triggers
        (200.0, 0.0, 0.0, RiskLevel.SEVERE),
        (0.0, 250.0, 0.0, RiskLevel.SEVERE),
        (0.0, 0.0, 150.0, RiskLevel.SEVERE),
        (350.0, 520.0, 185.0, RiskLevel.SEVERE),
    ],
)
def test_evaluate_values_threshold_matrix(
    r24: float, r48: float, api: float, expected_level: RiskLevel
) -> None:
    """Verify threshold boundary evaluation across all four tiers."""
    level, _ = RiskEvaluator.evaluate_values(r24, r48, api)
    assert level == expected_level


@pytest.mark.unit
def test_precedence_rule_api_dominant() -> None:
    """Verify that saturated soil (API >= 150) triggers SEVERE even under modest 24h rainfall."""
    # 24h rain is in MODERATE (65mm), but API is SEVERE (155.0)
    level, rules = RiskEvaluator.evaluate_values(
        rainfall_24h=65.0, rainfall_48h=70.0, antecedent_index=155.0
    )
    assert level == RiskLevel.SEVERE
    assert any("API index (155.0) >= 150.0" in r for r in rules)


@pytest.mark.unit
def test_precedence_rule_48h_dominant() -> None:
    """Verify that multi-day sustained downpour (48h >= 250) triggers SEVERE even if 24h is HIGH."""
    level, rules = RiskEvaluator.evaluate_values(
        rainfall_24h=120.0, rainfall_48h=265.0, antecedent_index=90.0
    )
    assert level == RiskLevel.SEVERE
    assert any("48h rainfall (265.0mm) >= 250.0mm" in r for r in rules)


@pytest.mark.unit
def test_audit_rules_formatting() -> None:
    """Verify human-readable audit rules are cleanly generated."""
    level, rules = RiskEvaluator.evaluate_values(
        rainfall_24h=162.0, rainfall_48h=180.0, antecedent_index=112.5
    )
    assert level == RiskLevel.HIGH
    assert len(rules) == 3
    assert "24h rainfall (162.0mm) >= 100.0mm" in rules
    assert "48h rainfall (180.0mm) >= 150.0mm" in rules
    assert "API index (112.5) >= 100.0" in rules


@pytest.mark.unit
def test_zero_baseline_empty_rules() -> None:
    """Zero rainfall baseline should return LOW with empty triggered_rules."""
    level, rules = RiskEvaluator.evaluate_values(0.0, 0.0, 0.0)
    assert level == RiskLevel.LOW
    assert rules == []


@pytest.mark.unit
def test_evaluate_metrics_integration() -> None:
    """Verify evaluate_metrics handles PrecipitationMetrics pydantic model."""
    metrics = PrecipitationMetrics(
        district_id="wayanad",
        timestamp=datetime(2026, 9, 6, 12, 0),
        rainfall_1h=15.0,
        rainfall_24h=215.0,
        rainfall_48h=320.0,
        rainfall_72h=400.0,
        antecedent_index=155.0,
    )
    level, rules = evaluate_metrics(metrics)
    assert level == RiskLevel.SEVERE
    assert len(rules) >= 2
