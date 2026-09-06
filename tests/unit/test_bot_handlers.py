"""Unit tests for Telegram bot command and callback query handlers (SPEC-004)."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from malabar_watch.bot.handlers import (
    callback_query_handler,
    disclaimer_command,
    help_command,
    history_command,
    start_command,
    status_command,
    subscribe_command,
    unsubscribe_command,
)
from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.storage import DatabaseManager


@pytest.fixture
def test_db():
    db = DatabaseManager(db_path=":memory:")
    db.initialize_schema()
    # Populate a sample observation for wayanad
    metrics = PrecipitationMetrics(
        district_id="wayanad",
        rainfall_1h=15.0,
        rainfall_24h=110.0,
        rainfall_48h=180.0,
        rainfall_72h=220.0,
        antecedent_index=95.0,
        timestamp=datetime(2026, 9, 6, 16, 0),
    )
    db.save_observation(metrics)
    return db


@pytest.fixture
def mock_context(test_db):
    context = MagicMock()
    context.bot_data = {"db": test_db}
    context.args = []
    return context


@pytest.fixture
def mock_update():
    update = MagicMock()
    update.effective_chat.id = 55555
    update.effective_message.reply_text = AsyncMock()
    return update


def _get_text(mock_func) -> str:
    call_args = mock_func.call_args
    if not call_args:
        return ""
    if "text" in call_args.kwargs:
        return call_args.kwargs["text"]
    if call_args.args:
        return str(call_args.args[0])
    return ""


@pytest.mark.asyncio
async def test_start_command(mock_update, mock_context):
    await start_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "Welcome to Malabar Watch" in _get_text(mock_update.effective_message.reply_text)


@pytest.mark.asyncio
async def test_help_command(mock_update, mock_context):
    await help_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "/status" in _get_text(mock_update.effective_message.reply_text)


@pytest.mark.asyncio
async def test_disclaimer_command(mock_update, mock_context):
    await disclaimer_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "1077" in _get_text(mock_update.effective_message.reply_text)


@pytest.mark.asyncio
async def test_status_command_with_arg(mock_update, mock_context):
    mock_context.args = ["wayanad"]
    await status_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    call_text = _get_text(mock_update.effective_message.reply_text)
    assert "MALABAR WATCH LIVE STATUS" in call_text
    assert "Wayanad" in call_text


@pytest.mark.asyncio
async def test_status_command_without_arg(mock_update, mock_context):
    mock_context.args = []
    await status_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    call_text = _get_text(mock_update.effective_message.reply_text)
    assert "Select a district" in call_text


@pytest.mark.asyncio
async def test_subscribe_and_unsubscribe_commands(mock_update, mock_context, test_db):
    # Subscribe to wayanad
    mock_context.args = ["wayanad"]
    await subscribe_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "Subscribed successfully" in _get_text(mock_update.effective_message.reply_text)

    sub = test_db.get_subscriber(55555)
    assert sub is not None
    assert sub["district_id"] == "wayanad"
    assert sub["is_active"] == 1

    # Unsubscribe
    mock_update.effective_message.reply_text.reset_mock()
    await unsubscribe_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "Unsubscribed" in _get_text(mock_update.effective_message.reply_text)

    sub_after = test_db.get_subscriber(55555)
    assert sub_after["is_active"] == 0


@pytest.mark.asyncio
async def test_history_command(mock_update, mock_context):
    mock_context.args = ["wayanad"]
    await history_command(mock_update, mock_context)
    mock_update.effective_message.reply_text.assert_called_once()
    assert "Rainfall Trend" in _get_text(mock_update.effective_message.reply_text)


@pytest.mark.asyncio
async def test_callback_query_handler(mock_update, mock_context, test_db):
    query = MagicMock()
    query.data = "sub:idukki"
    query.answer = AsyncMock()
    query.message.reply_text = AsyncMock()
    mock_update.callback_query = query

    await callback_query_handler(mock_update, mock_context)
    query.answer.assert_called_once()
    query.message.reply_text.assert_called_once()
    assert "Subscribed" in _get_text(query.message.reply_text)

    sub = test_db.get_subscriber(55555)
    assert sub["district_id"] == "idukki"
    assert sub["is_active"] == 1
