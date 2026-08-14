from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import MAX_STARS, TIER_CHANCE_PERCENT
from bot.constant.deck import CB_DECK_OPEN
from bot.constant.merge import (
    CB_MERGE_ACTION_PREFIX,
    CB_MERGE_ALL_TO_MAX,
    CB_MERGE_EVENTS,
    CB_MERGE_OPEN,
    CB_MERGE_STACK_PREFIX,
    CB_MERGE_TIER_PAGE_PREFIX,
    CB_MERGE_TIER_PREFIX,
)
from bot.db.repositories.inventory import OwnedStack
from bot.texts.common import BTN_BACK
from bot.texts.merge import (
    BTN_ALL_TO,
    BTN_BACK_STACKS,
    BTN_BACK_TIERS,
    BTN_EVENTS_TIER,
    BTN_MERGE_ALL_TO_MAX,
    BTN_NEXT_PAGE,
    BTN_PREV_PAGE,
    BTN_SINGLE_TO,
    STACK_BUTTON,
    TIER_BUTTON,
)

_PAGE_SIZE = 10


def merge_tier_picker() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=TIER_BUTTON.format(ubp=tier), callback_data=f"{CB_MERGE_TIER_PREFIX}{tier}")]
        for tier in sorted(TIER_CHANCE_PERCENT, reverse=True)
    ]
    rows.append([InlineKeyboardButton(text=BTN_EVENTS_TIER, callback_data=CB_MERGE_EVENTS)])
    # "Слить всё до Макс" — балк по ВСЕЙ текущей вселенной разом (все обычные тиры, без
    # выбора конкретного), см. CLAUDE.md. Сознательно не включает Ивенты-категорию.
    rows.append([InlineKeyboardButton(text=BTN_MERGE_ALL_TO_MAX, callback_data=CB_MERGE_ALL_TO_MAX)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stack_list(*, tier: int, stacks: list[OwnedStack], page: int) -> InlineKeyboardMarkup:
    total_pages = max(1, -(-len(stacks) // _PAGE_SIZE))
    page = max(1, min(page, total_pages))
    start = (page - 1) * _PAGE_SIZE
    chunk = stacks[start : start + _PAGE_SIZE]

    rows = [
        [
            InlineKeyboardButton(
                text=STACK_BUTTON.format(name=s.card.name, stars="🌟" * s.stars, quantity=s.quantity),
                callback_data=f"{CB_MERGE_STACK_PREFIX}{tier}:{s.card.id}:{s.stars}",
            )
        ]
        for s in chunk
    ]

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PREV_PAGE, callback_data=f"{CB_MERGE_TIER_PAGE_PREFIX}{tier}:{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text=BTN_NEXT_PAGE, callback_data=f"{CB_MERGE_TIER_PAGE_PREFIX}{tier}:{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=BTN_BACK_TIERS, callback_data=CB_MERGE_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_actions(*, tier: int, card_id: int, stars: int) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=BTN_SINGLE_TO.format(target=target),
                callback_data=f"{CB_MERGE_ACTION_PREFIX}{tier}:{card_id}:{stars}:{target}:1",
            ),
            InlineKeyboardButton(
                text=BTN_ALL_TO.format(target=target),
                callback_data=f"{CB_MERGE_ACTION_PREFIX}{tier}:{card_id}:{stars}:{target}:all",
            ),
        ]
        for target in range(stars + 1, MAX_STARS + 1)
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK_STACKS, callback_data=f"{CB_MERGE_TIER_PAGE_PREFIX}{tier}:1")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
