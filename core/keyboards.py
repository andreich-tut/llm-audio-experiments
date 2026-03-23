"""
Keyboard builders and UI label constants.
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# YouTube summary levels
YT_LEVEL_MAP = {"b": "brief", "d": "detailed", "k": "keypoints"}
YT_LEVEL_LABELS = {"brief": "Кратко", "detailed": "Подробно", "keypoints": "Тезисы"}

# Mode labels and descriptions
MODE_LABELS = {
    "chat": "💬 Чат",
    "transcribe": "🎙 Расшифровка",
    "note": "📓 Заметка",
}
MODE_DESCRIPTIONS = {
    "chat": "💬 Режим: чат — расшифровка + ответ LLM.",
    "transcribe": "🎙 Режим: только расшифровка голоса (без LLM).",
    "note": "📓 Режим: Obsidian-заметка — голос → структурированная заметка в Markdown.",
}


def yt_summary_keyboard(cache_key: str) -> InlineKeyboardMarkup:
    """Build inline keyboard with summary detail level buttons."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Кратко", callback_data=f"yt:b:{cache_key}"),
                InlineKeyboardButton(text="Подробно", callback_data=f"yt:d:{cache_key}"),
                InlineKeyboardButton(text="Тезисы", callback_data=f"yt:k:{cache_key}"),
            ]
        ]
    )


def mode_keyboard(current: str) -> InlineKeyboardMarkup:
    """Inline keyboard for mode selection. Current mode button is marked."""
    buttons = []
    for mode, label in MODE_LABELS.items():
        text = f"✅ {label}" if mode == current else label
        buttons.append(InlineKeyboardButton(text=text, callback_data=f"mode:{mode}"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def stop_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard with stop button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🛑 Стоп", callback_data="cancel"),
            ]
        ]
    )
