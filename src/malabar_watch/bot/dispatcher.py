"""Alert dispatcher for broadcasting bilingual advisories to Telegram subscribers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import Forbidden, RetryAfter, TelegramError

from malabar_watch.bot.formatter import format_alert_html
from malabar_watch.config import settings
from malabar_watch.storage import DatabaseManager

if TYPE_CHECKING:
    from malabar_watch.llm.models import BilingualAdvisory
    from malabar_watch.risk_engine.models import RiskAssessment

logger = logging.getLogger(__name__)


class AlertDispatcher:
    """Dispatches real-time early warnings to registered Telegram subscribers."""

    def __init__(
        self,
        bot: Bot | None = None,
        db: DatabaseManager | None = None,
    ) -> None:
        self.bot = bot
        self.db = db or DatabaseManager(db_path=settings.DATABASE_URL.replace("sqlite:///", ""))

    def _get_bot(self) -> Bot:
        """Lazily instantiates Bot if token is available."""
        if self.bot is not None:
            return self.bot
        if not settings.TELEGRAM_BOT_TOKEN:
            raise ValueError(
                "TELEGRAM_BOT_TOKEN is not configured. Cannot dispatch Telegram alerts."
            )
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        return self.bot

    async def dispatch_alert(
        self,
        assessment: RiskAssessment,
        advisory: BilingualAdvisory,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Broadcasts a bilingual risk alert to all active subscribers for the district.

        Args:
            assessment: Evaluated RiskAssessment model.
            advisory: Grounded BilingualAdvisory synthesized by DualLLMGateway.
            dry_run: If True, simulates dispatch without making actual Telegram API calls.

        Returns:
            Dictionary containing delivery stats: {'delivered': int, 'failed': int, 'total': int}
        """
        subscribers = self.db.get_subscribers(
            district_id=assessment.district, active_only=True
        )
        html_message = format_alert_html(assessment, advisory)

        delivered_count = 0
        failed_count = 0

        logger.info(
            "Initiating alert broadcast for district=%s, risk=%s to %d subscribers (dry_run=%s)",
            assessment.district,
            assessment.risk_level.value,
            len(subscribers),
            dry_run,
        )

        if dry_run or not settings.TELEGRAM_BOT_TOKEN:
            # Simulated broadcast
            logger.info("[Dry Run] Simulating delivery to %d subscribers", len(subscribers))
            delivered_count = len(subscribers)
        else:
            bot = self._get_bot()
            for sub in subscribers:
                chat_id = sub["chat_id"]
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=html_message,
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True,
                    )
                    delivered_count += 1
                    # Small throttle to avoid hitting Telegram flood limits (max 30 msgs/sec)
                    await asyncio.sleep(0.05)
                except Forbidden:
                    # User blocked the bot - deactivate in database
                    logger.warning(
                        "Bot was blocked by chat_id=%s. Deactivating subscription.", chat_id
                    )
                    self.db.remove_subscriber(chat_id)
                    failed_count += 1
                except RetryAfter as e:
                    sleep_sec = (
                        e.retry_after.total_seconds()
                        if hasattr(e.retry_after, "total_seconds")
                        else float(e.retry_after)
                    )
                    logger.warning(
                        "Telegram flood limit encountered. Sleeping for %.1f seconds.",
                        sleep_sec,
                    )
                    await asyncio.sleep(sleep_sec)
                    try:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=html_message,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True,
                        )
                        delivered_count += 1
                    except Exception as retry_err:
                        logger.error(
                            "Failed retry dispatch to chat_id=%s: %s", chat_id, retry_err
                        )
                        failed_count += 1
                except TelegramError as e:
                    logger.error("Telegram error sending alert to chat_id=%s: %s", chat_id, e)
                    failed_count += 1
                except Exception as e:
                    logger.error("Unexpected error sending alert to chat_id=%s: %s", chat_id, e)
                    failed_count += 1

        # Audit log into SQLite
        try:
            self.db.log_alert_dispatch(
                district_id=assessment.district,
                risk_level=assessment.risk_level.value,
                assessment_id=None,
                delivered_count=delivered_count,
                failed_count=failed_count,
            )
        except Exception as e:
            logger.error("Failed to write alert log to database: %s", e)

        return {
            "delivered": delivered_count,
            "failed": failed_count,
            "total": len(subscribers),
            "html_message": html_message,
        }
