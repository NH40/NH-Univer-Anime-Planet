from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.daily_bonus import CB_DAILY_BONUS_CLAIM
from bot.constant.profile import CB_PROFILE_OPEN
from bot.texts.common import BTN_BACK
from bot.texts.daily_bonus import BTN_CLAIM


def daily_bonus_menu(*, claimable: bool) -> InlineKeyboardMarkup:
    rows = []
    if claimable:
        rows.append([InlineKeyboardButton(text=BTN_CLAIM, callback_data=CB_DAILY_BONUS_CLAIM)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_PROFILE_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
