from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import CASINO_EMOJI, CASINO_ROLL_COST_COINS
from bot.constant.casino import (
    CB_CASINO_GAME_PREFIX,
    CB_CASINO_MASS_CONFIRM,
    CB_CASINO_MASS_PREFIX,
    CB_CASINO_OPEN,
    CB_CASINO_ROLL_PREFIX,
)
from bot.constant.shop import CB_SHOP_COINS
from bot.keyboards.shop import confirm_cancel_menu
from bot.texts.casino import BTN_MASS_ROLL, BTN_ROLL, GAME_NAMES
from bot.texts.common import BTN_BACK


def casino_menu() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{CASINO_EMOJI[game]} {GAME_NAMES[game]}", callback_data=f"{CB_CASINO_GAME_PREFIX}{game}"
            )
        ]
        for game in CASINO_EMOJI
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_COINS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def game_menu(game: str, *, allow_mass_roll: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=BTN_ROLL.format(price=CASINO_ROLL_COST_COINS),
                callback_data=f"{CB_CASINO_ROLL_PREFIX}{game}",
            )
        ]
    ]
    if allow_mass_roll:
        rows.append(
            [InlineKeyboardButton(text=BTN_MASS_ROLL, callback_data=f"{CB_CASINO_MASS_PREFIX}{game}")]
        )
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CASINO_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def mass_roll_confirm_menu() -> InlineKeyboardMarkup:
    return confirm_cancel_menu(CB_CASINO_MASS_CONFIRM)
