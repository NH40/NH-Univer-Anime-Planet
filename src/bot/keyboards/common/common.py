from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.texts.common import BTN_CLAN, BTN_DECK, BTN_DONATE, BTN_PASS, BTN_PROFILE, BTN_SETTINGS, BTN_SHOP


def main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_DECK)],
        [KeyboardButton(text=BTN_SHOP), KeyboardButton(text=BTN_CLAN)],
        [KeyboardButton(text=BTN_PASS), KeyboardButton(text=BTN_DONATE)],
        [KeyboardButton(text=BTN_SETTINGS)],
    ]
    # is_persistent=False (по явной просьбе пользователя 2026-08-06, см. CLAUDE.md) — даёт
    # клиенту Telegram показать стандартную стрелку сворачивания клавиатуры рядом с полем
    # ввода. is_persistent=True форсит клавиатуру всегда открытой без возможности свернуть.
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=False)
