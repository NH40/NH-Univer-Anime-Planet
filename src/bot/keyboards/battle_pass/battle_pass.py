from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.battle_pass import CB_BATTLE_PASS_CLAIM_FREE, CB_BATTLE_PASS_CLAIM_PREMIUM
from bot.constant.shop import CB_COINSHOP_BATTLE_PASS
from bot.texts.battle_pass import BTN_PASS_BUY, BTN_PASS_CLAIM_FREE, BTN_PASS_CLAIM_PREMIUM


def pass_menu(*, free_claimable: bool, premium_claimable: bool, is_premium: bool) -> InlineKeyboardMarkup:
    rows = []
    if free_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_FREE, callback_data=CB_BATTLE_PASS_CLAIM_FREE)])
    if premium_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_PREMIUM, callback_data=CB_BATTLE_PASS_CLAIM_PREMIUM)])
    if not is_premium:
        # Ведёт прямо в существующий экран покупки Battle Pass в магазине коинов
        # (handlers/shop) — не дублируем флоу оплаты здесь.
        rows.append([InlineKeyboardButton(text=BTN_PASS_BUY, callback_data=CB_COINSHOP_BATTLE_PASS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
