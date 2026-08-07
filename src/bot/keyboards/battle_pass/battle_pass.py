from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.constant.battle_pass import (
    CB_BATTLE_PASS_CLAIM_FREE,
    CB_BATTLE_PASS_CLAIM_PREMIUM,
    CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX,
    CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX,
    CB_BATTLE_PASS_LEVELS_PAGE_PREFIX,
    CB_BATTLE_PASS_OPEN,
)
from bot.constant.shop import CB_COINSHOP_BATTLE_PASS
from bot.texts.battle_pass import (
    BTN_PASS_APP,
    BTN_PASS_BACK,
    BTN_PASS_BUY,
    BTN_PASS_CLAIM_FREE,
    BTN_PASS_CLAIM_PREMIUM,
    BTN_PASS_LEVELS,
    BTN_PASS_PAGE_NEXT,
    BTN_PASS_PAGE_PREV,
)


def pass_menu(
    *, free_claimable: bool, premium_claimable: bool, is_premium: bool, mini_app_url: str | None = None
) -> InlineKeyboardMarkup:
    rows = []
    if free_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_FREE, callback_data=CB_BATTLE_PASS_CLAIM_FREE)])
    if premium_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_PREMIUM, callback_data=CB_BATTLE_PASS_CLAIM_PREMIUM)])
    if not is_premium:
        # Ведёт прямо в существующий экран покупки Battle Pass в магазине коинов
        # (handlers/shop) — не дублируем флоу оплаты здесь.
        rows.append([InlineKeyboardButton(text=BTN_PASS_BUY, callback_data=CB_COINSHOP_BATTLE_PASS)])
    rows.append([InlineKeyboardButton(text=BTN_PASS_LEVELS, callback_data=f"{CB_BATTLE_PASS_LEVELS_PAGE_PREFIX}1")])
    if mini_app_url:
        # ?view=battlepass — src/web/src/App.tsx читает это при загрузке и сразу открывает
        # вкладку Battle Pass вместо коллекции по умолчанию (тот же паттерн, что
        # ?view=profile у keyboards/profile.profile_menu).
        rows.append([InlineKeyboardButton(text=BTN_PASS_APP, web_app=WebAppInfo(url=f"{mini_app_url}?view=battlepass"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def levels_menu(
    *, page: int, total_pages: int, free_claimable: bool, premium_claimable: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if free_claimable:
        rows.append(
            [InlineKeyboardButton(text=BTN_PASS_CLAIM_FREE, callback_data=f"{CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX}{page}")]
        )
    if premium_claimable:
        rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_PASS_CLAIM_PREMIUM, callback_data=f"{CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX}{page}"
                )
            ]
        )

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PASS_PAGE_PREV, callback_data=f"{CB_BATTLE_PASS_LEVELS_PAGE_PREFIX}{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PASS_PAGE_NEXT, callback_data=f"{CB_BATTLE_PASS_LEVELS_PAGE_PREFIX}{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=BTN_PASS_BACK, callback_data=CB_BATTLE_PASS_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
