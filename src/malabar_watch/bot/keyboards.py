"""Inline keyboards for Telegram user interactions."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_district_keyboard(prefix: str = "status") -> InlineKeyboardMarkup:
    """Generates inline buttons for district selection.

    Args:
        prefix: Callback data prefix ('status' or 'sub').

    Returns:
        InlineKeyboardMarkup object.
    """
    keyboard = [
        [
            InlineKeyboardButton("📍 Wayanad (വയനാട്)", callback_data=f"{prefix}:wayanad"),
            InlineKeyboardButton("📍 Idukki (ഇടുക്കി)", callback_data=f"{prefix}:idukki"),
        ],
        [
            InlineKeyboardButton("📍 Kottayam (കോട്ടയം)", callback_data=f"{prefix}:kottayam"),
            InlineKeyboardButton("🌐 All Districts (എല്ലാം)", callback_data=f"{prefix}:all"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_action_keyboard(district: str) -> InlineKeyboardMarkup:
    """Generates quick action buttons for a district status view."""
    keyboard = [
        [
            InlineKeyboardButton(
                "🔔 Subscribe Alerts", callback_data=f"sub:{district}"
            ),
            InlineKeyboardButton(
                "📊 72h History", callback_data=f"hist:{district}"
            ),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Status", callback_data=f"status:{district}"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
