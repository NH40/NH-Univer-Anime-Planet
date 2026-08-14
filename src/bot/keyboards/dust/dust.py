from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import DUST_AMOUNT_PRESETS, TIER_CHANCE_PERCENT
from bot.constant.deck import CB_DECK_OPEN
from bot.constant.dust import (
    CB_DUST_ALL_ASK_PREFIX,
    CB_DUST_AMOUNT_ASK_PREFIX,
    CB_DUST_CUSTOM_PREFIX,
    CB_DUST_DUPES_ASK_PREFIX,
    CB_DUST_EVENTS,
    CB_DUST_MODE_ALL,
    CB_DUST_MODE_CANCEL,
    CB_DUST_MODE_DUPES,
    CB_DUST_OPEN,
    CB_DUST_SELECT,
    CB_DUST_STACK_PREFIX,
    CB_DUST_TIER_PAGE_PREFIX,
    CB_DUST_TIER_PREFIX,
)
from bot.db.repositories.inventory import OwnedStack
from bot.texts.common import BTN_BACK
from bot.texts.dust import (
    BTN_ALL,
    BTN_AMOUNT,
    BTN_BACK_STACKS,
    BTN_BACK_TIERS,
    BTN_CANCEL,
    BTN_CONFIRM,
    BTN_CUSTOM,
    BTN_DUPES,
    BTN_EVENTS_TIER,
    BTN_MODE_ALL,
    BTN_MODE_DUPES,
    BTN_MODE_SELECT,
    BTN_NEXT_PAGE,
    BTN_PREV_PAGE,
    STACK_BUTTON,
    TIER_BUTTON,
)

_PAGE_SIZE = 10


def mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_MODE_SELECT, callback_data=CB_DUST_SELECT)],
            [InlineKeyboardButton(text=BTN_MODE_ALL, callback_data=CB_DUST_MODE_ALL)],
            [InlineKeyboardButton(text=BTN_MODE_DUPES, callback_data=CB_DUST_MODE_DUPES)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)],
        ]
    )


def confirm_menu(confirm_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_CONFIRM, callback_data=confirm_callback),
                InlineKeyboardButton(text=BTN_CANCEL, callback_data=CB_DUST_MODE_CANCEL),
            ]
        ]
    )


def tier_picker() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=TIER_BUTTON.format(ubp=tier), callback_data=f"{CB_DUST_TIER_PREFIX}{tier}")]
        for tier in sorted(TIER_CHANCE_PERCENT, reverse=True)
    ]
    rows.append([InlineKeyboardButton(text=BTN_EVENTS_TIER, callback_data=CB_DUST_EVENTS)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DUST_OPEN)])
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
                callback_data=f"{CB_DUST_STACK_PREFIX}{tier}:{s.card.id}:{s.stars}",
            )
        ]
        for s in chunk
    ]

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PREV_PAGE, callback_data=f"{CB_DUST_TIER_PAGE_PREFIX}{tier}:{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(text=BTN_NEXT_PAGE, callback_data=f"{CB_DUST_TIER_PAGE_PREFIX}{tier}:{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton(text=BTN_BACK_TIERS, callback_data=CB_DUST_SELECT)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def card_actions(*, tier: int, card_id: int, stars: int) -> InlineKeyboardMarkup:
    """Каждая кнопка ведёт на экран подтверждения ("_ask"), не исполняет действие сразу —
    случайный тап не должен уничтожать карты без единого лишнего клика (подтверждено
    пользователем 2026-08-14)."""
    key = f"{tier}:{card_id}:{stars}"
    amount_row = [
        InlineKeyboardButton(text=BTN_AMOUNT.format(amount=n), callback_data=f"{CB_DUST_AMOUNT_ASK_PREFIX}{key}:{n}")
        for n in DUST_AMOUNT_PRESETS
    ]
    rows = [
        amount_row,
        [InlineKeyboardButton(text=BTN_CUSTOM, callback_data=f"{CB_DUST_CUSTOM_PREFIX}{key}")],
        [
            InlineKeyboardButton(text=BTN_DUPES, callback_data=f"{CB_DUST_DUPES_ASK_PREFIX}{key}"),
            InlineKeyboardButton(text=BTN_ALL, callback_data=f"{CB_DUST_ALL_ASK_PREFIX}{key}"),
        ],
        [InlineKeyboardButton(text=BTN_BACK_STACKS, callback_data=f"{CB_DUST_TIER_PAGE_PREFIX}{tier}:1")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def point_confirm_menu(*, confirm_callback: str, cancel_callback: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_CONFIRM, callback_data=confirm_callback),
                InlineKeyboardButton(text=BTN_CANCEL, callback_data=cancel_callback),
            ]
        ]
    )
