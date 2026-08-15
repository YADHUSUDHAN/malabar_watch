"""Risk engine module for rainfall and Antecedent Precipitation Index (API) evaluation."""

from enum import StrEnum
from typing import NamedTuple


class RiskLevel(StrEnum):
    """Multi-tier risk classification levels."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"


class AssessmentResult(NamedTuple):
    """Data transfer object representing risk evaluation output."""

    district: str
    risk_level: RiskLevel
    rainfall_24h_mm: float
    antecedent_index: float
    description: str


def evaluate_risk(
    district: str, rainfall_24h: float, api_index: float
) -> AssessmentResult:
    """Evaluates rainfall parameters against Kerala landslide threshold matrix."""
    if rainfall_24h >= 204.4 or api_index >= 150.0:
        level = RiskLevel.SEVERE
    elif rainfall_24h >= 150.0 or api_index >= 100.0:
        level = RiskLevel.HIGH
    elif rainfall_24h >= 100.0 or api_index >= 60.0:
        level = RiskLevel.MODERATE
    else:
        level = RiskLevel.LOW

    return AssessmentResult(
        district=district,
        risk_level=level,
        rainfall_24h_mm=rainfall_24h,
        antecedent_index=api_index,
        description=f"Risk assessment for {district}: {level.value}",
    )
