"""Unit tests for rainfall risk engine threshold evaluation."""

import pytest

from malabar_watch.risk_engine import RiskLevel, evaluate_risk


@pytest.mark.unit
@pytest.mark.parametrize(
    "rainfall_24h, api_index, expected_level",
    [
        (10.0, 20.0, RiskLevel.LOW),
        (105.0, 50.0, RiskLevel.MODERATE),
        (160.0, 80.0, RiskLevel.HIGH),
        (210.0, 160.0, RiskLevel.SEVERE),
    ],
)
def test_evaluate_risk_matrix(
    rainfall_24h: float, api_index: float, expected_level: RiskLevel
) -> None:
    """Test risk evaluation logic against various rainfall thresholds."""
    result = evaluate_risk("Wayanad", rainfall_24h, api_index)
    assert result.risk_level == expected_level
    assert result.district == "Wayanad"
