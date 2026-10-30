from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import DONATE_PRESETS_RUB
from bot.constant.donate import (
    CB_DONATE_CARD_PREFIX,
    CB_DONATE_CUSTOM,
    CB_DONATE_OPEN,
    CB_DONATE_PRESET_PREFIX,
    CB_DONATE_SBP_CHECK_PREFIX,
    CB_DONATE_SBP_PREFIX,
)
from bot.texts.donate import BTN_DONATE_BACK, BTN_DONATE_CUSTOM, BTN_PAY_CARD, BTN_PAY_SBP, BTN_SBP_CHECK, BTN_SBP_PAY

_PRESETS_PER_ROW = 3


def donate_menu() -> InlineKeyboardMarkup:
    preset_buttons = [
        InlineKeyboardButton(text=f"{amount} ₽", callback_data=f"{CB_DONATE_PRESET_PREFIX}{amount}")
        for amount in DONATE_PRESETS_RUB
    ]
    rows = [preset_buttons[i : i + _PRESETS_PER_ROW] for i in range(0, len(preset_buttons), _PRESETS_PER_ROW)]
    rows.append([InlineKeyboardButton(text=BTN_DONATE_CUSTOM, callback_data=CB_DONATE_CUSTOM)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def method_menu(amount_rub: int, sbp: bool, card: bool) -> InlineKeyboardMarkup:
    rows = []
    if sbp:
        rows.append([InlineKeyboardButton(text=BTN_PAY_SBP, callback_data=f"{CB_DONATE_SBP_PREFIX}{amount_rub}")])
    if card:
        rows.append([InlineKeyboardButton(text=BTN_PAY_CARD, callback_data=f"{CB_DONATE_CARD_PREFIX}{amount_rub}")])
    rows.append([InlineKeyboardButton(text=BTN_DONATE_BACK, callback_data=CB_DONATE_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sbp_menu(payment_id: int, amount_rub: int, url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=BTN_SBP_PAY.format(amount=amount_rub), url=url)],
        [InlineKeyboardButton(text=BTN_SBP_CHECK, callback_data=f"{CB_DONATE_SBP_CHECK_PREFIX}{payment_id}")],
        [InlineKeyboardButton(text=BTN_DONATE_BACK, callback_data=CB_DONATE_OPEN)],
    ])


def back_to_donate() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_DONATE_BACK, callback_data=CB_DONATE_OPEN)]])
