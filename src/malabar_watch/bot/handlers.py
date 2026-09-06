import logging
from datetime import datetime
from typing import Any, cast

from telegram import Message, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from malabar_watch.bot.formatter import (
    format_disclaimer_html,
    format_help_html,
    format_history_html,
    format_status_html,
    format_welcome_html,
    get_micro_zone_label,
)
from malabar_watch.bot.keyboards import get_action_keyboard, get_district_keyboard
from malabar_watch.config import now_ist, settings
from malabar_watch.ingestion import DEFAULT_TARGETS, DataIngestionService
from malabar_watch.ingestion.models import PrecipitationMetrics
from malabar_watch.llm import DualLLMGateway
from malabar_watch.risk_engine import RiskAssessmentService
from malabar_watch.storage import DatabaseManager

logger = logging.getLogger(__name__)


def get_db(context: ContextTypes.DEFAULT_TYPE) -> DatabaseManager:
    """Retrieves or initializes the DatabaseManager stored in bot data."""
    if "db" not in context.bot_data:
        db_path = settings.DATABASE_URL.replace("sqlite:///", "")
        context.bot_data["db"] = DatabaseManager(db_path=db_path)
    return cast(DatabaseManager, context.bot_data["db"])


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /start command with welcome greeting and district selector."""
    if not update.effective_message:
        return
    text = format_welcome_html()
    await update.effective_message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_district_keyboard("status"),
        disable_web_page_preview=True,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /help command displaying available commands and instructions."""
    if not update.effective_message:
        return
    text = format_help_html()
    await update.effective_message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def disclaimer_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /disclaimer command displaying safety scope and emergency contacts."""
    if not update.effective_message:
        return
    text = format_disclaimer_html()
    await update.effective_message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# Cache for synthesized advisories: (district, risk_level, hour_str) -> BilingualAdvisory
_ADVISORY_CACHE: dict[tuple[str, str, str], Any] = {}


async def fetch_or_get_status(
    district_id: str, db: DatabaseManager
) -> tuple[PrecipitationMetrics, Any, Any]:
    """Helper to fetch or retrieve latest metrics and assessment for a district."""
    norm_district = district_id.lower().strip()
    obs = db.get_latest_observation(norm_district)

    if obs:
        ts_raw = obs.get("timestamp")
        ts = datetime.fromisoformat(str(ts_raw)) if ts_raw else now_ist()
        metrics = PrecipitationMetrics(
            district_id=norm_district,
            rainfall_1h=float(obs.get("precipitation_mm", 0.0)),
            rainfall_24h=float(obs.get("rainfall_24h", 0.0)),
            rainfall_48h=float(obs.get("rainfall_48h", 0.0)),
            rainfall_72h=float(obs.get("rainfall_72h", 0.0)),
            antecedent_index=float(obs.get("antecedent_index", 0.0)),
            timestamp=ts,
        )
    else:
        # On-demand live fetch if database is empty
        ingest = DataIngestionService()
        target = DEFAULT_TARGETS.get(norm_district)
        if target:
            metrics = await ingest.fetch_and_process_district(target)
            db.save_observation(metrics)
        else:
            raise ValueError(f"Unknown district '{district_id}'.")

    # Assess risk
    risk_service = RiskAssessmentService(db_manager=db)
    assessment = risk_service.assess_metrics(metrics)

    # If risk is elevated, synthesize advisory if not already present in hourly cache
    advisory = None
    if assessment.requires_alert:
        hour_key = (
            norm_district,
            assessment.risk_level.value,
            metrics.timestamp.strftime("%Y-%m-%d %H"),
        )
        if hour_key in _ADVISORY_CACHE:
            advisory = _ADVISORY_CACHE[hour_key]
        else:
            gateway = DualLLMGateway()
            advisory = await gateway.generate_advisory(assessment)
            _ADVISORY_CACHE[hour_key] = advisory

    return metrics, assessment, advisory


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /status [district] command."""
    if not update.effective_message:
        return

    db = get_db(context)
    args = context.args or []

    if not args:
        await update.effective_message.reply_text(
            "📍 <b>Select a district to view live rainfall and landslide risk:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_district_keyboard("status"),
        )
        return

    district_arg = args[0].lower().strip()
    if district_arg not in DEFAULT_TARGETS and district_arg != "all":
        valid = ", ".join(DEFAULT_TARGETS.keys())
        await update.effective_message.reply_text(
            f"❌ Unknown district '<code>{district_arg}</code>'.\nValid options: {valid}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_district_keyboard("status"),
        )
        return

    try:
        metrics, assessment, advisory = await fetch_or_get_status(district_arg, db)
        text = format_status_html(metrics, assessment, advisory)
        await update.effective_message.reply_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_action_keyboard(district_arg),
            disable_web_page_preview=True,
        )
    except Exception as e:
        logger.error("Error evaluating status for %s: %s", district_arg, e)
        await update.effective_message.reply_text(
            f"⚠️ Could not retrieve live status for {district_arg}: {e}"
        )


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /subscribe [district] command."""
    if not update.effective_message or not update.effective_chat:
        return

    db = get_db(context)
    chat_id = update.effective_chat.id
    args = context.args or []

    if not args:
        await update.effective_message.reply_text(
            "🔔 <b>Select a district to receive automated early-warning alerts:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_district_keyboard("sub"),
        )
        return

    district_arg = args[0].lower().strip()
    if district_arg not in DEFAULT_TARGETS and district_arg != "all":
        valid = ", ".join(list(DEFAULT_TARGETS.keys()) + ["all"])
        await update.effective_message.reply_text(
            f"❌ Unknown district '<code>{district_arg}</code>'.\nValid options: {valid}",
            parse_mode=ParseMode.HTML,
        )
        return

    db.add_subscriber(chat_id=chat_id, district_id=district_arg)
    if district_arg == "all":
        label = "All Micro-Zones (എല്ലാ മേഖലകളും)"
    else:
        label = get_micro_zone_label(district_arg)

    await update.effective_message.reply_text(
        f"✅ <b>Subscribed successfully!</b>\n"
        f"You will now receive automated bilingual alerts for <b>{label}</b> "
        f"whenever risk levels escalate.\n\n"
        f"<i>Send /unsubscribe at any time to opt-out.</i>",
        parse_mode=ParseMode.HTML,
    )


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /unsubscribe command."""
    if not update.effective_message or not update.effective_chat:
        return

    db = get_db(context)
    chat_id = update.effective_chat.id

    removed = db.remove_subscriber(chat_id=chat_id)
    if removed:
        await update.effective_message.reply_text(
            "🛑 <b>Unsubscribed.</b> You will no longer receive automated alert notifications.\n"
            "You can resubscribe anytime using /subscribe.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.effective_message.reply_text(
            "ℹ️ You do not have an active subscription.\nUse /subscribe to enable alerts.",
            parse_mode=ParseMode.HTML,
        )


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles /history [district] command."""
    if not update.effective_message:
        return

    db = get_db(context)
    args = context.args or []

    if not args:
        await update.effective_message.reply_text(
            "📈 <b>Select a district to view trailing rainfall history:</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_district_keyboard("hist"),
        )
        return

    district_arg = args[0].lower().strip()
    history = db.get_rainfall_history(district_arg, hours=72)
    text = format_history_html(district_arg, history)

    await update.effective_message.reply_text(
        text=text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_action_keyboard(district_arg),
        disable_web_page_preview=True,
    )


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user taps on inline keyboard buttons."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    data = query.data
    db = get_db(context)
    chat_id = update.effective_chat.id if update.effective_chat else None

    if ":" not in data:
        return

    action, target = data.split(":", 1)

    if action == "status":
        if target == "all":
            # For 'all', display summary of all primary micro-zones
            for d_id in ["wayanad", "idukki", "kottayam"]:
                try:
                    metrics, assessment, advisory = await fetch_or_get_status(d_id, db)
                    text = format_status_html(metrics, assessment, advisory)
                    if isinstance(query.message, Message):
                        await query.message.reply_text(
                            text=text,
                            parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True,
                        )
                except Exception as e:
                    logger.error("Failed querying status for %s: %s", d_id, e)
        else:
            try:
                metrics, assessment, advisory = await fetch_or_get_status(target, db)
                text = format_status_html(metrics, assessment, advisory)
                if isinstance(query.message, Message):
                    await query.message.reply_text(
                        text=text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=get_action_keyboard(target),
                        disable_web_page_preview=True,
                    )
            except Exception as e:
                logger.error("Failed querying status for %s: %s", target, e)
                if isinstance(query.message, Message):
                    await query.message.reply_text(f"⚠️ Error retrieving status for {target}: {e}")

    elif action == "sub":
        if chat_id:
            db.add_subscriber(chat_id=chat_id, district_id=target)
            label = "All Micro-Zones (എല്ലാം)" if target == "all" else get_micro_zone_label(target)
            if isinstance(query.message, Message):
                await query.message.reply_text(
                    f"✅ <b>Subscribed to alerts for {label}!</b>\n"
                    "You will receive instant bilingual alerts whenever risk escalates.\n"
                    "Send /unsubscribe anytime to stop.",
                    parse_mode=ParseMode.HTML,
                )

    elif action == "hist":
        history = db.get_rainfall_history(target, hours=72)
        text = format_history_html(target, history)
        if isinstance(query.message, Message):
            await query.message.reply_text(
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_action_keyboard(target),
                disable_web_page_preview=True,
            )
