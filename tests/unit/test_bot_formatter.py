"""Unit tests for Telegram HTML formatting utilities (SPEC-004)."""

from datetime import datetime

from malabar_watch.bot.formatter import (
    format_alert_html,
    format_disclaimer_html,
    format_help_html,
    format_history_html,
    format_status_html,
    format_welcome_html,
    get_micro_zone_label,
)
from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.llm.models import BilingualAdvisory, LLMProviderType
from malabar_watch.risk_engine.models import (
    EscalationState,
    HistoricalEvent,
    RiskAssessment,
    RiskLevel,
)


def test_get_micro_zone_label():
    label = get_micro_zone_label("wayanad")
    assert "Wayanad" in label
    assert "Vythiri" in label

    # Unknown fallback
    assert get_micro_zone_label("calicut") == "Calicut"


def test_format_alert_html_with_historical_context():
    hist = HistoricalEvent(
        event_id="wayanad_2024",
        district="wayanad",
        location="Chooralmala / Meppadi",
        date="July 2024",
        rainfall_24h_mm=372.0,
        rainfall_48h_mm=570.0,
        consequence="Catastrophic landslides and debris flows after extreme antecedent rainfall.",
        key_trigger="Extreme antecedent saturation",
        analog_threshold_level="SEVERE",
    )
    assessment = RiskAssessment(
        district="wayanad",
        assessed_at=datetime(2026, 9, 6, 16, 0),
        risk_level=RiskLevel.SEVERE,
        escalation_state=EscalationState.ESCALATED,
        rainfall_1h=30.0,
        rainfall_24h=215.0,
        rainfall_48h=310.0,
        rainfall_72h=360.0,
        antecedent_index=158.0,
        triggered_rules=["R24h >= 200mm", "API >= 150"],
        historical_event=hist,
        requires_alert=True,
    )
    advisory = BilingualAdvisory(
        district_id="wayanad",
        risk_level=RiskLevel.SEVERE,
        summary_en="Severe rainfall in Wayanad with high landslide threat.",
        advisory_en="Evacuate from steep slopes immediately.",
        summary_ml="വയനാട്ടിൽ അതിതീവ്ര മഴയും ഉരുൾപൊട്ടൽ ഭീഷണിയും.",
        advisory_ml="ഉടൻ സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക.",
        provider_used=LLMProviderType.GEMINI,
        latency_ms=1200,
    )

    html_out = format_alert_html(assessment, advisory)

    assert "MALABAR WATCH WARNING" in html_out
    assert "മലബാർ വാച്ച് മുന്നറിയിപ്പ്" in html_out
    assert "🔴 <b>RED ALERT / ചുവപ്പ് അലർട്ട് (SEVERE)</b>" in html_out
    assert "215.0 mm" in html_out
    assert "Chooralmala" in html_out
    assert "വയനാട്ടിൽ അതിതീവ്ര മഴ" in html_out
    assert "KSDMA" in html_out


def test_format_status_html():
    metrics = PrecipitationMetrics(
        district_id="idukki",
        rainfall_1h=5.0,
        rainfall_24h=45.0,
        rainfall_48h=70.0,
        rainfall_72h=85.0,
        antecedent_index=55.0,
        timestamp=datetime(2026, 9, 6, 16, 0),
    )
    assessment = RiskAssessment(
        district="idukki",
        assessed_at=datetime(2026, 9, 6, 16, 0),
        risk_level=RiskLevel.LOW,
        escalation_state=EscalationState.SUSTAINED,
        rainfall_1h=5.0,
        rainfall_24h=45.0,
        rainfall_48h=70.0,
        rainfall_72h=85.0,
        antecedent_index=55.0,
        triggered_rules=[],
        historical_event=None,
        requires_alert=False,
    )

    html_out = format_status_html(metrics, assessment)

    assert "MALABAR WATCH LIVE STATUS" in html_out
    assert "🟢 <b>LOW RISK / ഹരിതം</b>" in html_out
    assert "Idukki (North / High Range)" in html_out
    assert "45.0 mm" in html_out


def test_format_history_html():
    # Empty case
    empty_out = format_history_html("kottayam", [])
    assert "No recent rainfall observations recorded" in empty_out

    # Populated case
    records = [
        {
            "timestamp": "2026-09-06T16:00:00",
            "precipitation_mm": 12.5,
            "rainfall_24h": 110.0,
            "antecedent_index": 95.0,
        },
        {
            "timestamp": "2026-09-06T15:00:00",
            "precipitation_mm": 8.0,
            "rainfall_24h": 98.0,
            "antecedent_index": 90.0,
        },
    ]
    html_out = format_history_html("kottayam", records)
    assert "Rainfall Trend" in html_out
    assert "12.5" in html_out
    assert "110.0" in html_out


def test_format_static_templates():
    welcome = format_welcome_html()
    assert "Welcome to Malabar Watch" in welcome
    assert "/status" in welcome

    help_text = format_help_html()
    assert "/subscribe" in help_text
    assert "Wayanad" in help_text

    disclaimer = format_disclaimer_html()
    assert "KSDMA" in disclaimer
    assert "1077" in disclaimer
    assert "112" in disclaimer
