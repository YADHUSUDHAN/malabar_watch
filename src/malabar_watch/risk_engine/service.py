import logging
from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING

from malabar_watch.risk_engine.evaluator import RiskEvaluator
from malabar_watch.risk_engine.historical import HistoricalContextStore
from malabar_watch.risk_engine.models import (
    EscalationState,
    RiskAssessment,
    RiskLevel,
)
from malabar_watch.storage import DatabaseManager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from malabar_watch.ingestion.models import PrecipitationMetrics


class RiskAssessmentService:
    """Evaluates precipitation metrics, tracks state transitions, and persists assessments."""

    def __init__(
        self,
        db_manager: DatabaseManager | None = None,
        historical_store: HistoricalContextStore | None = None,
        evaluator: type[RiskEvaluator] = RiskEvaluator,
        enable_hysteresis: bool = True,
        heartbeat_cooldown_hours: float = 6.0,
        burst_threshold_1h: float = 25.0,
    ) -> None:
        self.db = db_manager or DatabaseManager()
        self.historical_store = historical_store or HistoricalContextStore()
        self.evaluator = evaluator
        self.enable_hysteresis = enable_hysteresis
        self.heartbeat_cooldown_hours = heartbeat_cooldown_hours
        self.burst_threshold_1h = burst_threshold_1h

        # Ensure database tables exist
        self.db.initialize_schema()

    def assess_metrics(
        self,
        metrics: "PrecipitationMetrics",
        assessed_at: datetime | None = None,
        persist: bool = True,
    ) -> RiskAssessment:
        """Evaluates metrics against threshold rules, calculates state transition, and persists.

        Args:
            metrics: Input PrecipitationMetrics for a district/micro-zone.
            assessed_at: Optional custom assessment timestamp (defaults to metrics.timestamp).
            persist: Whether to save the resulting RiskAssessment into SQLite.

        Returns:
            Computed RiskAssessment instance with transition state and historical precedent.
        """
        timestamp = assessed_at or metrics.timestamp
        raw_level, raw_rules = self.evaluator.evaluate_metrics(metrics)

        # Retrieve the latest existing assessment for delta evaluation
        latest = self.db.get_latest_assessment(metrics.district_id)

        if latest is None:
            # First assessment for district
            state = EscalationState.FIRST_ASSESSMENT
            requires_alert = raw_level in (
                RiskLevel.MODERATE,
                RiskLevel.HIGH,
                RiskLevel.SEVERE,
            )
            final_level = raw_level
            final_rules = list(raw_rules)
        else:
            prev_level = RiskLevel(str(latest["risk_level"]))

            if raw_level.severity_rank > prev_level.severity_rank:
                # Severity escalated: immediate alert required
                state = EscalationState.ESCALATED
                requires_alert = True
                final_level = raw_level
                final_rules = list(raw_rules)

            elif raw_level.severity_rank == prev_level.severity_rank:
                # Severity sustained: alert suppressed unless burst or heartbeat expires
                state = EscalationState.SUSTAINED
                final_level = raw_level
                final_rules = list(raw_rules)

                is_burst = metrics.rainfall_1h >= self.burst_threshold_1h

                last_alert_time = self.db.get_latest_alert_time(metrics.district_id)
                is_heartbeat_expired = False
                if last_alert_time is not None:
                    diff_seconds = (timestamp - last_alert_time).total_seconds()
                    if diff_seconds >= self.heartbeat_cooldown_hours * 3600:
                        is_heartbeat_expired = True
                elif final_level in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE):
                    is_heartbeat_expired = True

                if is_burst:
                    requires_alert = True
                    final_rules.append(
                        f"Hourly burst ({metrics.rainfall_1h:.1f}mm >= "
                        f"{self.burst_threshold_1h:.1f}mm) triggered alert dispatch"
                    )
                elif is_heartbeat_expired and final_level in (
                    RiskLevel.MODERATE,
                    RiskLevel.HIGH,
                    RiskLevel.SEVERE,
                ):
                    requires_alert = True
                    final_rules.append(
                        f"Heartbeat interval ({self.heartbeat_cooldown_hours:.0f}h) "
                        f"elapsed for sustained {final_level.value}"
                    )
                else:
                    requires_alert = False

            else:
                # Severity is lower: evaluate hysteresis
                if self.enable_hysteresis:
                    prev_eval_level, _ = self.evaluator.evaluate_values(
                        rainfall_24h=float(latest["rainfall_24h"]),
                        rainfall_48h=float(latest["rainfall_48h"]),
                        antecedent_index=float(latest["antecedent_index"]),
                    )
                    # If the previous observation was already below or at raw_level,
                    # the reduction has persisted for 2 consecutive evaluations.
                    if prev_eval_level.severity_rank <= raw_level.severity_rank:
                        state = EscalationState.DOWNGRADED
                        final_level = raw_level
                        final_rules = list(raw_rules)
                        requires_alert = prev_level in (RiskLevel.HIGH, RiskLevel.SEVERE)
                    else:
                        # Hold previous level for 1 evaluation cycle to prevent threshold flickering
                        state = EscalationState.SUSTAINED
                        final_level = prev_level
                        _, prev_rules = self.evaluator.evaluate_values(
                            rainfall_24h=float(latest["rainfall_24h"]),
                            rainfall_48h=float(latest["rainfall_48h"]),
                            antecedent_index=float(latest["antecedent_index"]),
                        )
                        final_rules = list(prev_rules)
                        final_rules.append(
                            f"Hysteresis hold: metrics dropped to {raw_level.value}; "
                            f"holding {final_level.value} for 2 consecutive cycles below threshold"
                        )
                        requires_alert = False

                else:
                    state = EscalationState.DOWNGRADED
                    final_level = raw_level
                    final_rules = list(raw_rules)
                    requires_alert = prev_level in (RiskLevel.HIGH, RiskLevel.SEVERE)

        # Match regional historical landslide disaster precedent for HIGH or SEVERE
        historical_precedent = self.historical_store.find_precedent(
            district=metrics.district_id,
            risk_level=final_level,
            rainfall_24h=metrics.rainfall_24h,
        )

        assessment = RiskAssessment(
            district=metrics.district_id,
            assessed_at=timestamp,
            risk_level=final_level,
            escalation_state=state,
            rainfall_1h=metrics.rainfall_1h,
            rainfall_24h=metrics.rainfall_24h,
            rainfall_48h=metrics.rainfall_48h,
            rainfall_72h=metrics.rainfall_72h,
            antecedent_index=metrics.antecedent_index,
            triggered_rules=final_rules,
            historical_event=historical_precedent,
            requires_alert=requires_alert,
        )

        if persist:
            row_id = self.db.save_assessment(assessment)
            logger.info(
                "Risk assessed for '%s': level=%s, state=%s, requires_alert=%s (row_id=%d)",
                assessment.district,
                assessment.risk_level.value,
                assessment.escalation_state.value,
                assessment.requires_alert,
                row_id,
            )
        else:
            logger.info(
                "Risk assessed for '%s': level=%s, state=%s, requires_alert=%s (unpersisted)",
                assessment.district,
                assessment.risk_level.value,
                assessment.escalation_state.value,
                assessment.requires_alert,
            )

        return assessment

    def assess_all(
        self,
        metrics_dict: Mapping[str, "PrecipitationMetrics"],
        persist: bool = True,
    ) -> dict[str, RiskAssessment]:
        """Runs risk evaluation across all ingested district metrics."""
        assessments: dict[str, RiskAssessment] = {}
        for district_id, metrics in metrics_dict.items():
            assessments[district_id] = self.assess_metrics(metrics, persist=persist)
        return assessments
