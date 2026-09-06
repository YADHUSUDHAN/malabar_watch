"""Integration tests for risk assessment persistence, transitions, and suppression logic."""

from datetime import datetime, timedelta

import pytest

from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.risk_engine import (
    EscalationState,
    RiskAssessmentService,
    RiskLevel,
)
from malabar_watch.storage import DatabaseManager


@pytest.fixture
def test_db() -> DatabaseManager:
    manager = DatabaseManager(db_path=":memory:")
    manager.initialize_schema()
    return manager


@pytest.mark.integration
def test_risk_assessment_storage_end_to_end(test_db: DatabaseManager) -> None:
    """Verify end-to-end flow from metrics to persisted risk_assessments in SQLite."""
    service = RiskAssessmentService(db_manager=test_db)
    now = datetime(2026, 9, 6, 10, 0)

    metrics = PrecipitationMetrics(
        district_id="wayanad",
        timestamp=now,
        rainfall_1h=12.0,
        rainfall_24h=210.0,
        rainfall_48h=340.0,
        rainfall_72h=390.0,
        antecedent_index=165.0,
    )

    assessment = service.assess_metrics(metrics)

    assert assessment.risk_level == RiskLevel.SEVERE
    assert assessment.escalation_state == EscalationState.FIRST_ASSESSMENT
    assert assessment.requires_alert is True
    assert assessment.historical_event is not None
    assert assessment.historical_event.event_id == "wayanad_2024"

    # Verify database persistence
    saved = test_db.get_latest_assessment("wayanad")
    assert saved is not None
    assert saved["district"] == "wayanad"
    assert saved["risk_level"] == "SEVERE"
    assert saved["escalation_state"] == "FIRST_ASSESSMENT"
    assert saved["rainfall_24h"] == 210.0
    assert saved["requires_alert"] == 1
    assert saved["historical_event_id"] == "wayanad_2024"
    assert isinstance(saved["triggered_rules"], list)
    assert len(saved["triggered_rules"]) >= 2


@pytest.mark.integration
def test_state_transitions_and_alert_suppression(test_db: DatabaseManager) -> None:
    """Verify transition states: FIRST_ASSESSMENT -> ESCALATED -> SUSTAINED -> BURST."""
    service = RiskAssessmentService(db_manager=test_db)
    t0 = datetime(2026, 9, 6, 8, 0)

    # 1. First assessment at LOW: no alert required
    m1 = PrecipitationMetrics(
        district_id="idukki",
        timestamp=t0,
        rainfall_1h=2.0,
        rainfall_24h=30.0,
        rainfall_48h=50.0,
        rainfall_72h=60.0,
        antecedent_index=40.0,
    )
    a1 = service.assess_metrics(m1)
    assert a1.escalation_state == EscalationState.FIRST_ASSESSMENT
    assert a1.risk_level == RiskLevel.LOW
    assert a1.requires_alert is False

    # 2. Escalation to MODERATE: requires immediate alert
    t1 = t0 + timedelta(hours=1)
    m2 = PrecipitationMetrics(
        district_id="idukki",
        timestamp=t1,
        rainfall_1h=10.0,
        rainfall_24h=75.0,
        rainfall_48h=95.0,
        rainfall_72h=110.0,
        antecedent_index=70.0,
    )
    a2 = service.assess_metrics(m2)
    assert a2.escalation_state == EscalationState.ESCALATED
    assert a2.risk_level == RiskLevel.MODERATE
    assert a2.requires_alert is True

    # 3. Steady at MODERATE: sustained, alert suppressed
    t2 = t1 + timedelta(hours=1)
    m3 = PrecipitationMetrics(
        district_id="idukki",
        timestamp=t2,
        rainfall_1h=4.0,
        rainfall_24h=78.0,
        rainfall_48h=98.0,
        rainfall_72h=115.0,
        antecedent_index=72.0,
    )
    a3 = service.assess_metrics(m3)
    assert a3.escalation_state == EscalationState.SUSTAINED
    assert a3.risk_level == RiskLevel.MODERATE
    assert a3.requires_alert is False  # Alert fatigue suppressed!

    # 4. Steady at MODERATE, but sudden 1h burst >= 25mm: alert dispatched
    t3 = t2 + timedelta(hours=1)
    m4 = PrecipitationMetrics(
        district_id="idukki",
        timestamp=t3,
        rainfall_1h=28.0,  # Extreme burst
        rainfall_24h=85.0,
        rainfall_48h=105.0,
        rainfall_72h=120.0,
        antecedent_index=75.0,
    )
    a4 = service.assess_metrics(m4)
    assert a4.escalation_state == EscalationState.SUSTAINED
    assert a4.requires_alert is True
    assert any("Hourly burst" in r for r in a4.triggered_rules)


@pytest.mark.integration
def test_heartbeat_cooldown_for_sustained_risk(test_db: DatabaseManager) -> None:
    """Verify sustained risk tier refreshes alert once 6-hour heartbeat cooldown expires."""
    service = RiskAssessmentService(db_manager=test_db, heartbeat_cooldown_hours=6.0)
    t0 = datetime(2026, 9, 6, 2, 0)

    # Initial escalation to HIGH at 02:00 -> alert dispatched
    m1 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t0,
        rainfall_1h=15.0,
        rainfall_24h=120.0,
        rainfall_48h=160.0,
        rainfall_72h=180.0,
        antecedent_index=110.0,
    )
    a1 = service.assess_metrics(m1)
    assert a1.requires_alert is True

    # 4 hours later (06:00): still HIGH, alert suppressed (< 6h)
    t1 = t0 + timedelta(hours=4)
    m2 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t1,
        rainfall_1h=5.0,
        rainfall_24h=125.0,
        rainfall_48h=165.0,
        rainfall_72h=185.0,
        antecedent_index=112.0,
    )
    a2 = service.assess_metrics(m2)
    assert a2.escalation_state == EscalationState.SUSTAINED
    assert a2.requires_alert is False

    # 7 hours after initial alert (09:00): heartbeat cooldown expired -> alert dispatched
    t2 = t0 + timedelta(hours=7)
    m3 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t2,
        rainfall_1h=6.0,
        rainfall_24h=122.0,
        rainfall_48h=162.0,
        rainfall_72h=182.0,
        antecedent_index=110.0,
    )
    a3 = service.assess_metrics(m3)
    assert a3.escalation_state == EscalationState.SUSTAINED
    assert a3.requires_alert is True
    assert any("Heartbeat interval" in r for r in a3.triggered_rules)


@pytest.mark.integration
def test_hysteresis_prevents_threshold_flickering(test_db: DatabaseManager) -> None:
    """Verify hysteresis holds alert tier for 1 period before confirming downgrade."""
    service = RiskAssessmentService(db_manager=test_db, enable_hysteresis=True)
    t0 = datetime(2026, 9, 6, 12, 0)

    # Hour 1: HIGH level (105mm 24h)
    m1 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t0,
        rainfall_1h=10.0,
        rainfall_24h=105.0,
        rainfall_48h=130.0,
        rainfall_72h=140.0,
        antecedent_index=80.0,
    )
    a1 = service.assess_metrics(m1)
    assert a1.risk_level == RiskLevel.HIGH

    # Hour 2: Rain dips slightly below threshold (98mm, MODERATE)
    # 1st hour below threshold -> Hysteresis holds HIGH (SUSTAINED)
    t1 = t0 + timedelta(hours=1)
    m2 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t1,
        rainfall_1h=2.0,
        rainfall_24h=98.0,
        rainfall_48h=120.0,
        rainfall_72h=130.0,
        antecedent_index=75.0,
    )
    a2 = service.assess_metrics(m2)
    assert a2.risk_level == RiskLevel.HIGH
    assert a2.escalation_state == EscalationState.SUSTAINED
    assert a2.requires_alert is False
    assert any("Hysteresis hold" in r for r in a2.triggered_rules)

    # Hour 3: Rain stays below threshold (95mm, MODERATE)
    # 2nd consecutive hour below threshold -> Downgrade confirmed!
    t2 = t1 + timedelta(hours=1)
    m3 = PrecipitationMetrics(
        district_id="kottayam",
        timestamp=t2,
        rainfall_1h=1.0,
        rainfall_24h=95.0,
        rainfall_48h=118.0,
        rainfall_72h=128.0,
        antecedent_index=72.0,
    )
    a3 = service.assess_metrics(m3)
    assert a3.risk_level == RiskLevel.MODERATE
    assert a3.escalation_state == EscalationState.DOWNGRADED
    # Dispatches recovery advisory because previous confirmed tier was HIGH
    assert a3.requires_alert is True
