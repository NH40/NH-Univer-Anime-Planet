from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import DONATE_PRESETS_RUB
from bot.constant.donate import CB_DONATE_CUSTOM, CB_DONATE_PRESET_PREFIX
from bot.texts.donate import BTN_DONATE_CUSTOM

_PRESETS_PER_ROW = 3


def donate_menu() -> InlineKeyboardMarkup:
    preset_buttons = [
        InlineKeyboardButton(text=f"{amount} ₽", callback_data=f"{CB_DONATE_PRESET_PREFIX}{amount}")
        for amount in DONATE_PRESETS_RUB
    ]
    rows = [preset_buttons[i : i + _PRESETS_PER_ROW] for i in range(0, len(preset_buttons), _PRESETS_PER_ROW)]
    rows.append([InlineKeyboardButton(text=BTN_DONATE_CUSTOM, callback_data=CB_DONATE_CUSTOM)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
