from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.help import HELP_SECTIONS
from bot.constant.help import CB_HELP_OPEN, CB_HELP_SECTION_PREFIX
from bot.texts.common import BTN_BACK


def help_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=s.title, callback_data=f"{CB_HELP_SECTION_PREFIX}{s.code}")]
        for s in HELP_SECTIONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_section_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_HELP_OPEN)]])
