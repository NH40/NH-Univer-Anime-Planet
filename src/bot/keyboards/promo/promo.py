from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.promo import CB_PROMO_REDEEM_CANCEL
from bot.texts.common import BTN_BACK


def redeem_prompt_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_PROMO_REDEEM_CANCEL)]])
