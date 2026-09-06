"""Unit tests for Dual-LLM gateway, prompt building, sanitization, and failover cascade."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from malabar_watch.llm import DualLLMGateway, LLMProviderType
from malabar_watch.llm.gemini import GeminiProvider
from malabar_watch.llm.groq import GroqProvider
from malabar_watch.llm.prompts import build_advisory_prompt, sanitize_json_output
from malabar_watch.llm.templates import generate_template_advisory
from malabar_watch.risk_engine.models import (
    EscalationState,
    HistoricalEvent,
    RiskAssessment,
    RiskLevel,
)


@pytest.fixture
def sample_severe_assessment() -> RiskAssessment:
    return RiskAssessment(
        district="wayanad",
        assessed_at=datetime(2026, 9, 6, 12, 0),
        risk_level=RiskLevel.SEVERE,
        escalation_state=EscalationState.ESCALATED,
        rainfall_1h=28.0,
        rainfall_24h=215.0,
        rainfall_48h=365.0,
        rainfall_72h=410.0,
        antecedent_index=158.0,
        triggered_rules=["24h rainfall (215.0mm) >= 200.0mm", "API index (158.0) >= 150.0"],
        historical_event=HistoricalEvent(
            event_id="wayanad_2024",
            district="wayanad",
            location="Chooralmala / Mundakkai / Meppadi",
            date="July 2024",
            rainfall_24h_mm=372.0,
            consequence="Catastrophic debris flow",
            key_trigger="Cloudburst on saturated laterite soil",
            analog_threshold_level="SEVERE",
        ),
        requires_alert=True,
    )


@pytest.mark.unit
def test_build_advisory_prompt(sample_severe_assessment: RiskAssessment) -> None:
    """Verify prompt builder formats all metrics, rules, and historical grounding."""
    prompt = build_advisory_prompt(sample_severe_assessment)
    assert "Wayanad" in prompt
    assert "SEVERE" in prompt
    assert "215.0 mm" in prompt
    assert "158.0" in prompt
    assert "Chooralmala / Mundakkai" in prompt
    assert "Catastrophic debris flow" in prompt


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_input, expected_json",
    [
        (
            '{"summary_en": "Rain is heavy", "summary_ml": "മഴ ശക്തമാണ്", '
            '"advisory_en": "Be safe", "advisory_ml": "ശ്രദ്ധിക്കുക"}',
            '{"summary_en": "Rain is heavy", "summary_ml": "മഴ ശക്തമാണ്", '
            '"advisory_en": "Be safe", "advisory_ml": "ശ്രദ്ധിക്കുക"}',
        ),
        (
            '```json\n{"summary_en": "Rain", "summary_ml": "മഴ", '
            '"advisory_en": "Stay alert", "advisory_ml": "ജാഗ്രത"}\n```',
            '{"summary_en": "Rain", "summary_ml": "മഴ", '
            '"advisory_en": "Stay alert", "advisory_ml": "ജാഗ്രത"}',
        ),
        (
            'Here is the response:\n```\n{"summary_en": "High rain", '
            '"summary_ml": "മഴ", "advisory_en": "Evacuate", "advisory_ml": "മാറുക"}\n```\n'
            "Hope this helps!",
            '{"summary_en": "High rain", "summary_ml": "മഴ", '
            '"advisory_en": "Evacuate", "advisory_ml": "മാറുക"}',
        ),
    ],
)
def test_sanitize_json_output(raw_input: str, expected_json: str) -> None:
    """Verify markdown fences and noise are cleanly stripped."""
    assert sanitize_json_output(raw_input) == expected_json


@pytest.mark.unit
@pytest.mark.parametrize(
    "tier", [RiskLevel.LOW, RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE]
)
def test_deterministic_template_fallback_tiers(tier: RiskLevel) -> None:
    """Verify template generator produces valid bilingual output for all 4 tiers."""
    assessment = RiskAssessment(
        district="idukki",
        assessed_at=datetime(2026, 9, 6, 12, 0),
        risk_level=tier,
        escalation_state=EscalationState.FIRST_ASSESSMENT,
        rainfall_1h=5.0,
        rainfall_24h=80.0,
        rainfall_48h=110.0,
        rainfall_72h=130.0,
        antecedent_index=75.0,
        triggered_rules=[],
        requires_alert=tier in (RiskLevel.MODERATE, RiskLevel.HIGH, RiskLevel.SEVERE),
    )
    advisory = generate_template_advisory(assessment, latency_ms=5)

    assert advisory.district_id == "idukki"
    assert advisory.risk_level == tier
    assert advisory.provider_used == LLMProviderType.TEMPLATE.value
    assert len(advisory.summary_en) > 10
    assert len(advisory.summary_ml) > 10
    assert len(advisory.advisory_en) > 10
    assert len(advisory.advisory_ml) > 10


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gateway_primary_gemini_success(sample_severe_assessment: RiskAssessment) -> None:
    """Verify gateway uses Gemini when primary responds successfully."""
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.is_available = True
    mock_gemini.generate_advisory.return_value = {
        "summary_en": "Extreme rain recorded in Wayanad.",
        "summary_ml": "വയനാട്ടിൽ അതിതീവ്ര മഴ രേഖപ്പെടുത്തി.",
        "advisory_en": "Move to safe shelters immediately.",
        "advisory_ml": "സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക.",
    }

    mock_groq = AsyncMock(spec=GroqProvider)
    mock_groq.is_available = True

    gateway = DualLLMGateway(gemini_provider=mock_gemini, groq_provider=mock_groq)
    advisory = await gateway.generate_advisory(sample_severe_assessment)

    assert advisory.provider_used == LLMProviderType.GEMINI.value
    assert advisory.risk_level == RiskLevel.SEVERE
    assert "Wayanad" in advisory.summary_en
    mock_gemini.generate_advisory.assert_awaited_once()
    mock_groq.generate_advisory.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gateway_failover_to_groq(sample_severe_assessment: RiskAssessment) -> None:
    """Verify gateway automatically switches to Groq when Gemini fails (timeout or 429)."""
    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.is_available = True
    mock_gemini.generate_advisory.side_effect = TimeoutError("Gemini timed out")

    mock_groq = AsyncMock(spec=GroqProvider)
    mock_groq.is_available = True
    mock_groq.generate_advisory.return_value = {
        "summary_en": "Groq: Critical rainfall in Wayanad.",
        "summary_ml": "ഗ്രോക്ക്: വയനാട്ടിൽ അതിതീവ്ര മഴ.",
        "advisory_en": "Evacuate high-risk hill slopes.",
        "advisory_ml": "ദുരന്തസാധ്യതാ പ്രദേശങ്ങളിൽ നിന്ന് മാറുക.",
    }

    gateway = DualLLMGateway(gemini_provider=mock_gemini, groq_provider=mock_groq)
    advisory = await gateway.generate_advisory(sample_severe_assessment)

    assert advisory.provider_used == LLMProviderType.GROQ.value
    assert "Groq:" in advisory.summary_en
    mock_gemini.generate_advisory.assert_awaited_once()
    mock_groq.generate_advisory.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_gateway_failover_to_template_when_all_fail(
    sample_severe_assessment: RiskAssessment,
) -> None:
    """Verify gateway falls back to deterministic template when both Gemini and Groq fail."""

    mock_gemini = AsyncMock(spec=GeminiProvider)
    mock_gemini.is_available = True
    mock_gemini.generate_advisory.side_effect = RuntimeError("Gemini API error")

    mock_groq = AsyncMock(spec=GroqProvider)
    mock_groq.is_available = True
    mock_groq.generate_advisory.side_effect = RuntimeError("Groq 429 quota error")

    gateway = DualLLMGateway(gemini_provider=mock_gemini, groq_provider=mock_groq)
    advisory = await gateway.generate_advisory(sample_severe_assessment)

    assert advisory.provider_used == LLMProviderType.TEMPLATE.value
    assert advisory.risk_level == RiskLevel.SEVERE
    assert len(advisory.summary_en) > 0
    assert len(advisory.summary_ml) > 0
