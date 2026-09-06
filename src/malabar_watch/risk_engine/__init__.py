"""Risk engine module for deterministic landslide risk evaluation and historical grounding."""

from datetime import datetime

from malabar_watch.config import now_ist
from malabar_watch.risk_engine.evaluator import RiskEvaluator, evaluate_metrics
from malabar_watch.risk_engine.historical import HistoricalContextStore
from malabar_watch.risk_engine.models import (
    EscalationState,
    HistoricalEvent,
    RiskAssessment,
    RiskLevel,
)
from malabar_watch.risk_engine.service import RiskAssessmentService

# Backward compatibility alias
AssessmentResult = RiskAssessment


def evaluate_risk(
    district: str,
    rainfall_24h: float,
    api_index: float,
    rainfall_48h: float = 0.0,
    rainfall_1h: float = 0.0,
    rainfall_72h: float = 0.0,
    assessed_at: datetime | None = None,
) -> RiskAssessment:
    """Convenience evaluation function evaluating raw metrics against calibrated matrix.

    Maintains backward compatibility with legacy calls while returning full RiskAssessment.
    """
    timestamp = assessed_at or now_ist()
    level, rules = RiskEvaluator.evaluate_values(
        rainfall_24h=rainfall_24h,
        rainfall_48h=rainfall_48h,
        antecedent_index=api_index,
    )

    store = HistoricalContextStore()
    precedent = store.find_precedent(district, level, rainfall_24h)

    return RiskAssessment(
        district=district,
        assessed_at=timestamp,
        risk_level=level,
        escalation_state=EscalationState.FIRST_ASSESSMENT,
        rainfall_1h=rainfall_1h,
        rainfall_24h=rainfall_24h,
        rainfall_48h=rainfall_48h,
        rainfall_72h=rainfall_72h,
        antecedent_index=api_index,
        triggered_rules=rules,
        historical_event=precedent,
        requires_alert=level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE),
    )


__all__ = [
    "AssessmentResult",
    "EscalationState",
    "HistoricalContextStore",
    "HistoricalEvent",
    "RiskAssessment",
    "RiskAssessmentService",
    "RiskEvaluator",
    "RiskLevel",
    "evaluate_metrics",
    "evaluate_risk",
]
