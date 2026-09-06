"""Unit tests for AlertDispatcher (SPEC-004)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram.error import Forbidden, RetryAfter

from malabar_watch.bot.dispatcher import AlertDispatcher
from malabar_watch.llm.models import BilingualAdvisory, LLMProviderType
from malabar_watch.risk_engine.models import (
    EscalationState,
    HistoricalEvent,
    RiskAssessment,
    RiskLevel,
)
from malabar_watch.storage import DatabaseManager


@pytest.fixture
def mock_db():
    db = DatabaseManager(db_path=":memory:")
    db.initialize_schema()
    db.add_subscriber(chat_id=101, district_id="wayanad")
    db.add_subscriber(chat_id=102, district_id="wayanad")
    db.add_subscriber(chat_id=103, district_id="idukki")
    db.add_subscriber(chat_id=999, district_id="all")
    return db


@pytest.fixture
def sample_assessment():
    return RiskAssessment(
        district="wayanad",
        assessed_at=datetime(2026, 9, 6, 16, 0),
        risk_level=RiskLevel.SEVERE,
        escalation_state=EscalationState.ESCALATED,
        rainfall_1h=28.0,
        rainfall_24h=215.0,
        rainfall_48h=310.0,
        rainfall_72h=350.0,
        antecedent_index=158.0,
        triggered_rules=["R24h >= 200mm"],
        historical_event=HistoricalEvent(
            event_id="wayanad_2024",
            district="wayanad",
            location="Chooralmala / Meppadi",
            date="July 2024",
            rainfall_24h_mm=372.0,
            rainfall_48h_mm=570.0,
            consequence="Massive debris flows.",
            key_trigger="Excess saturation",
            analog_threshold_level="SEVERE",
        ),
        requires_alert=True,
    )


@pytest.fixture
def sample_advisory():
    return BilingualAdvisory(
        district_id="wayanad",
        risk_level=RiskLevel.SEVERE,
        summary_en="Severe rainfall in Wayanad.",
        advisory_en="Evacuate from slopes.",
        summary_ml="വയനാട്ടിൽ അതിതീവ്ര മഴ.",
        advisory_ml="ഉടൻ സുരക്ഷിത സ്ഥാനങ്ങളിലേക്ക് മാറുക.",
        provider_used=LLMProviderType.GEMINI,
        latency_ms=950,
    )


@pytest.mark.asyncio
async def test_dispatcher_dry_run(mock_db, sample_assessment, sample_advisory):
    dispatcher = AlertDispatcher(bot=None, db=mock_db)
    stats = await dispatcher.dispatch_alert(
        assessment=sample_assessment,
        advisory=sample_advisory,
        dry_run=True,
    )

    # Wayanad subscribers: chat 101, 102, plus 999 ('all') = 3
    assert stats["total"] == 3
    assert stats["delivered"] == 3
    assert stats["failed"] == 0
    assert "MALABAR WATCH WARNING" in stats["html_message"]


@pytest.mark.asyncio
async def test_dispatcher_live_delivery_and_blocked_user(
    mock_db, sample_assessment, sample_advisory
):
    mock_bot = MagicMock()
    # Let chat 101 succeed, chat 102 fail with Forbidden (blocked bot), chat 999 succeed
    async def send_side_effect(chat_id, **kwargs):
        if chat_id == 102:
            raise Forbidden("Bot was blocked by the user")
        return MagicMock()

    mock_bot.send_message = AsyncMock(side_effect=send_side_effect)

    dispatcher = AlertDispatcher(bot=mock_bot, db=mock_db)
    stats = await dispatcher.dispatch_alert(
        assessment=sample_assessment,
        advisory=sample_advisory,
        dry_run=False,
    )

    assert stats["total"] == 3
    assert stats["delivered"] == 2
    assert stats["failed"] == 1

    # Verify chat 102 was deactivated in SQLite
    sub_102 = mock_db.get_subscriber(102)
    assert sub_102["is_active"] == 0

    # Verify chat 101 remains active
    sub_101 = mock_db.get_subscriber(101)
    assert sub_101["is_active"] == 1
