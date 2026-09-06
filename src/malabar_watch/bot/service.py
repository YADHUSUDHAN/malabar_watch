"""Telegram Bot Service managing lifecycle, handler registration, and long polling."""

from __future__ import annotations

import logging
from typing import Any

from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
)

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
from malabar_watch.config import settings
from malabar_watch.storage import DatabaseManager

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Orchestrates python-telegram-bot Application and long polling execution."""

    def __init__(
        self,
        token: str | None = None,
        db: DatabaseManager | None = None,
    ) -> None:
        self.token = token or settings.TELEGRAM_BOT_TOKEN
        self.db = db or DatabaseManager(db_path=settings.DATABASE_URL.replace("sqlite:///", ""))
        self.application: Application[Any, Any, Any, Any, Any, Any] | None = None

    def build_application(self) -> Application[Any, Any, Any, Any, Any, Any]:
        """Configures and registers all commands and callback query handlers."""
        if not self.token:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not set. Please set the environment variable "
                "or define it in your .env file."
            )

        app = ApplicationBuilder().token(self.token).build()

        # Share database manager in bot data
        app.bot_data["db"] = self.db

        # Register command handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("status", status_command))
        app.add_handler(CommandHandler("subscribe", subscribe_command))
        app.add_handler(CommandHandler("unsubscribe", unsubscribe_command))
        app.add_handler(CommandHandler("history", history_command))
        app.add_handler(CommandHandler("disclaimer", disclaimer_command))
        app.add_handler(CommandHandler("help", help_command))

        # Register inline button callback handler
        app.add_handler(CallbackQueryHandler(callback_query_handler))

        self.application = app
        return app

    def run_polling(self) -> None:
        """Starts outbound long polling (blocking call). Zero open inbound ports."""
        from malabar_watch.logging import setup_logging

        setup_logging()
        app = self.build_application()
        logger.info(
            "Starting Malabar Watch Telegram bot in long-polling mode (Zero Inbound Ports)..."
        )
        app.run_polling(drop_pending_updates=True)
