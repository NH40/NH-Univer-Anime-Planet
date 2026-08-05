from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import MERGE_COPIES_REQUIRED, TIER_CHANCE_PERCENT
from bot.constant.collection import (
    CB_COLL_DUST1_PREFIX,
    CB_COLL_DUSTALL_PREFIX,
    CB_COLL_MERGE_PREFIX,
    CB_COLL_NAV_PREFIX,
    CB_COLL_TIER_PREFIX,
)
from bot.constant.deck import CB_DECK_COLLECTION, CB_DECK_OPEN
from bot.texts.collection import (
    BTN_BACK_TIERS,
    BTN_DUST_ALL,
    BTN_DUST_ONE,
    BTN_MERGE,
    BTN_NEXT_1,
    BTN_NEXT_5,
    BTN_PREV_1,
    BTN_PREV_5,
    TIER_BUTTON,
)
from bot.texts.common import BTN_BACK


def tier_picker() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=TIER_BUTTON.format(ubp=tier), callback_data=f"{CB_COLL_TIER_PREFIX}{tier}")]
        for tier in sorted(TIER_CHANCE_PERCENT, reverse=True)
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stack_view(*, tier: int, index: int, total: int, quantity: int) -> InlineKeyboardMarkup:
    nav_row = []
    if index - 5 >= 0:
        nav_row.append(InlineKeyboardButton(text=BTN_PREV_5, callback_data=f"{CB_COLL_NAV_PREFIX}{tier}:{index - 5}"))
    if index - 1 >= 0:
        nav_row.append(InlineKeyboardButton(text=BTN_PREV_1, callback_data=f"{CB_COLL_NAV_PREFIX}{tier}:{index - 1}"))
    if index + 1 < total:
        nav_row.append(InlineKeyboardButton(text=BTN_NEXT_1, callback_data=f"{CB_COLL_NAV_PREFIX}{tier}:{index + 1}"))
    if index + 5 < total:
        nav_row.append(InlineKeyboardButton(text=BTN_NEXT_5, callback_data=f"{CB_COLL_NAV_PREFIX}{tier}:{index + 5}"))

    rows = [nav_row] if nav_row else []

    action_row = []
    if quantity > 1:
        action_row.append(
            InlineKeyboardButton(text=BTN_DUST_ONE, callback_data=f"{CB_COLL_DUST1_PREFIX}{tier}:{index}")
        )
    action_row.append(
        InlineKeyboardButton(text=BTN_DUST_ALL, callback_data=f"{CB_COLL_DUSTALL_PREFIX}{tier}:{index}")
    )
    rows.append(action_row)

    if quantity >= MERGE_COPIES_REQUIRED:
        rows.append(
            [InlineKeyboardButton(text=BTN_MERGE, callback_data=f"{CB_COLL_MERGE_PREFIX}{tier}:{index}")]
        )

    rows.append([InlineKeyboardButton(text=BTN_BACK_TIERS, callback_data=CB_DECK_COLLECTION)])
    return InlineKeyboardMarkup(inline_keyboard=rows)
