"""Pydantic data models and enumerations for deterministic risk engine."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """Multi-tier geotechnical landslide risk severity levels."""

    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"

    @property
    def severity_rank(self) -> int:
        """Returns integer rank for severity ordering and transition deltas."""
        ranks = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.SEVERE: 3,
        }
        return ranks[self]

    @property
    def badge(self) -> str:
        """Returns bilingual color badge for terminal/alert display."""
        badges = {
            RiskLevel.LOW: "🟢 Green / ഹരിതം",
            RiskLevel.MODERATE: "🟡 Yellow / മഞ്ഞ",
            RiskLevel.HIGH: "🟠 Orange / ഓറഞ്ച്",
            RiskLevel.SEVERE: "🔴 Red / ചുവപ്പ്",
        }
        return badges[self]

    @property
    def malayalam_label(self) -> str:
        """Returns Malayalam translation of the risk level."""
        labels = {
            RiskLevel.LOW: "ഹരിതം (കുറഞ്ഞ അപകടസാധ്യത)",
            RiskLevel.MODERATE: "മഞ്ഞ (ജാഗ്രത പുലർത്തുക)",
            RiskLevel.HIGH: "ഓറഞ്ച് (ഉയർന്ന അപകടസാധ്യത)",
            RiskLevel.SEVERE: "ചുവപ്പ് (തീവ്ര അടിയന്തരാവസ്ഥ)",
        }
        return labels[self]


class EscalationState(StrEnum):
    """State transition delta relative to previous assessment."""

    FIRST_ASSESSMENT = "FIRST_ASSESSMENT"
    ESCALATED = "ESCALATED"
    SUSTAINED = "SUSTAINED"
    DOWNGRADED = "DOWNGRADED"


class HistoricalEvent(BaseModel):
    """Verified historical landslide disaster precedent for regional context grounding."""

    event_id: str = Field(description="Unique event slug (e.g. 'wayanad_2024')")
    district: str = Field(description="Primary district identifier")
    location: str = Field(description="Specific hills, villages, or taluk")
    date: str = Field(description="Month and year of disaster occurrence")
    rainfall_24h_mm: float = Field(description="Peak single-day / 24h rainfall (mm)")
    rainfall_48h_mm: float | None = Field(
        default=None, description="Cumulative 48-hour rainfall (mm)"
    )
    consequence: str = Field(description="Casualties and geotechnical damage impact")
    key_trigger: str = Field(description="Soil saturation / meteorological failure trigger")
    analog_threshold_level: str = Field(description="Analog risk level tier ('HIGH' or 'SEVERE')")


class RiskAssessment(BaseModel):
    """Immutable deterministic evaluation output payload."""

    district: str = Field(description="District or micro-zone identifier")
    assessed_at: datetime = Field(description="Timestamp when assessment was performed")
    risk_level: RiskLevel = Field(description="Deterministic risk severity tier")
    escalation_state: EscalationState = Field(
        description="Transition status compared to previous assessment"
    )
    rainfall_1h: float = Field(description="Precipitation in latest completed hour (mm)")
    rainfall_24h: float = Field(description="Trailing 24-hour cumulative precipitation (mm)")
    rainfall_48h: float = Field(description="Trailing 48-hour cumulative precipitation (mm)")
    rainfall_72h: float = Field(description="Trailing 72-hour cumulative precipitation (mm)")
    antecedent_index: float = Field(description="Antecedent Precipitation Index (API)")
    triggered_rules: list[str] = Field(
        default_factory=list, description="Audit log of specific threshold rules triggered"
    )
    historical_event: HistoricalEvent | None = Field(
        default=None, description="Matched historical precedent for HIGH/SEVERE tiers"
    )
    requires_alert: bool = Field(
        default=False, description="Whether alert dispatch is mandated by transition logic"
    )

    @property
    def rainfall_24h_mm(self) -> float:
        """Compatibility property for legacy callers."""
        return self.rainfall_24h

    @property
    def description(self) -> str:
        """Formatted summary description for logging and display."""
        return (
            f"Risk assessment for {self.district}: "
            f"{self.risk_level.value} ({self.escalation_state.value})"
        )
