from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import RELIC_GAME_EMOJI
from bot.constant.celestial import (
    CB_CELESTIAL_ACCEPT_PREFIX,
    CB_CELESTIAL_CARD_PREFIX,
    CB_CELESTIAL_DECLINE_CONFIRM_PREFIX,
    CB_CELESTIAL_DECLINE_PREFIX,
    CB_CELESTIAL_OPEN,
    CB_CELESTIAL_THROW_PREFIX,
)
from bot.constant.deck import CB_DECK_OPEN
from bot.db.repositories.celestial import CelestialCardStatus
from bot.texts.celestial import (
    BTN_CELESTIAL_ACCEPT,
    BTN_CELESTIAL_DECLINE,
    BTN_CELESTIAL_THROW,
    CELESTIAL_LIST_BUTTON_CONTESTED,
    CELESTIAL_LIST_BUTTON_FREE,
    CELESTIAL_LIST_BUTTON_OWNED,
    GAME_NAMES,
)
from bot.texts.common import BTN_BACK


def celestial_list_menu(statuses: list[CelestialCardStatus]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for status in statuses:
        if status.ownership is None:
            label = CELESTIAL_LIST_BUTTON_FREE.format(name=status.card.name)
        elif status.ownership.challenger_id is not None:
            label = CELESTIAL_LIST_BUTTON_CONTESTED.format(name=status.card.name)
        else:
            label = CELESTIAL_LIST_BUTTON_OWNED.format(name=status.card.name)
        rows.append([InlineKeyboardButton(text=label, callback_data=f"{CB_CELESTIAL_CARD_PREFIX}{status.card.id}")])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def celestial_detail_menu(
    status: CelestialCardStatus, *, viewer_id: int, current_game: str | None, can_throw: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    ownership = status.ownership
    card_id = status.card.id

    if status.battle is not None and can_throw and current_game is not None:
        emoji = RELIC_GAME_EMOJI.get(current_game, "🎲")
        name = GAME_NAMES.get(current_game, current_game)
        rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_CELESTIAL_THROW.format(emoji=emoji, game=name),
                    callback_data=f"{CB_CELESTIAL_THROW_PREFIX}{card_id}",
                )
            ]
        )
    elif (
        status.battle is None
        and ownership is not None
        and ownership.challenger_id is not None
        and ownership.owner_id == viewer_id
    ):
        rows.append([InlineKeyboardButton(text=BTN_CELESTIAL_ACCEPT, callback_data=f"{CB_CELESTIAL_ACCEPT_PREFIX}{card_id}")])
        rows.append([InlineKeyboardButton(text=BTN_CELESTIAL_DECLINE, callback_data=f"{CB_CELESTIAL_DECLINE_PREFIX}{card_id}")])

    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_CELESTIAL_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def decline_confirm_menu(card_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚠️ Да, отказаться", callback_data=f"{CB_CELESTIAL_DECLINE_CONFIRM_PREFIX}{card_id}"
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=f"{CB_CELESTIAL_CARD_PREFIX}{card_id}")],
        ]
    )


def push_accept_decline_menu(card_id: int) -> InlineKeyboardMarkup:
    """Клавиатура ПРЯМО ПОД пуш-уведомлением владельцу о новом претенденте (см.
    CLAUDE.md) — принять можно сразу; отказ всё равно ведёт через подтверждение
    (decline_confirm_menu), необратимое действие не должно уходить в один клик из пуша."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CELESTIAL_ACCEPT, callback_data=f"{CB_CELESTIAL_ACCEPT_PREFIX}{card_id}")],
            [InlineKeyboardButton(text=BTN_CELESTIAL_DECLINE, callback_data=f"{CB_CELESTIAL_DECLINE_PREFIX}{card_id}")],
        ]
    )


def push_throw_menu(card_id: int, *, game: str) -> InlineKeyboardMarkup:
    emoji = RELIC_GAME_EMOJI.get(game, "🎲")
    name = GAME_NAMES.get(game, game)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_CELESTIAL_THROW.format(emoji=emoji, game=name),
                    callback_data=f"{CB_CELESTIAL_THROW_PREFIX}{card_id}",
                )
            ]
        ]
    )
