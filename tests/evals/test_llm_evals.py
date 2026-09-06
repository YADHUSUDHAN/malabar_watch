"""LLM evaluation benchmark suite for bilingual advisory validation."""

import re
from datetime import datetime

import pytest

from malabar_watch.llm import BilingualAdvisory, DualLLMGateway
from malabar_watch.risk_engine.models import EscalationState, RiskAssessment, RiskLevel


@pytest.mark.evals
@pytest.mark.asyncio
async def test_gateway_bilingual_response_schema() -> None:
    """Verify dual LLM gateway returns valid BilingualAdvisory model."""
    gateway = DualLLMGateway()
    assessment = RiskAssessment(
        district="wayanad",
        assessed_at=datetime.now(),
        risk_level=RiskLevel.HIGH,
        escalation_state=EscalationState.ESCALATED,
        rainfall_1h=15.0,
        rainfall_24h=140.0,
        rainfall_48h=180.0,
        rainfall_72h=210.0,
        antecedent_index=115.0,
        triggered_rules=["24h rainfall (140.0mm) >= 100.0mm"],
        requires_alert=True,
    )

    advisory = await gateway.generate_advisory(assessment)

    assert isinstance(advisory, BilingualAdvisory)
    assert advisory.district_id == "wayanad"
    assert advisory.risk_level == RiskLevel.HIGH
    assert len(advisory.summary_en) > 10
    assert len(advisory.summary_ml) > 10
    assert len(advisory.advisory_en) > 10
    assert len(advisory.advisory_ml) > 10


@pytest.mark.evals
@pytest.mark.asyncio
async def test_malayalam_character_set_and_keywords() -> None:
    """Verify Malayalam text contains authentic Malayalam characters and disaster keywords."""
    gateway = DualLLMGateway()
    assessment = RiskAssessment(
        district="kottayam",
        assessed_at=datetime.now(),
        risk_level=RiskLevel.SEVERE,
        escalation_state=EscalationState.ESCALATED,
        rainfall_1h=30.0,
        rainfall_24h=220.0,
        rainfall_48h=310.0,
        rainfall_72h=360.0,
        antecedent_index=160.0,
        triggered_rules=["24h rainfall (220.0mm) >= 200.0mm"],
        requires_alert=True,
    )

    advisory = await gateway.generate_advisory(assessment)

    malayalam_text = f"{advisory.summary_ml} {advisory.advisory_ml}"

    # Verify Malayalam Unicode block (\u0D00 - \u0D7F) is present
    malayalam_chars = re.findall(r"[\u0D00-\u0D7F]", malayalam_text)
    assert len(malayalam_chars) > 20, "Response must contain authentic Malayalam script"

    # Verify authentic disaster keywords (landslide, warning, alert, emergency)
    disaster_keywords = ["ഉരുൾപൊട്ടൽ", "മണ്ണിടിച്ചിൽ", "ജാഗ്രത", "അലർട്ട്", "റെഡ്", "മഴ", "സുരക്ഷിത"]
    matches = [kw for kw in disaster_keywords if kw in malayalam_text]
    assert len(matches) >= 2, f"Expected disaster keywords in Malayalam output, found: {matches}"


@pytest.mark.evals
@pytest.mark.asyncio
async def test_legacy_generate_bilingual_advisory_compatibility() -> None:
    """Verify backward compatibility with legacy dictionary generation interface."""
    gateway = DualLLMGateway()
    response = await gateway.generate_bilingual_advisory("Generate Wayanad warning")

    assert "english" in response
    assert "malayalam" in response
    assert len(response["english"]) > 0
    assert len(response["malayalam"]) > 0
