from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.texts.common import (
    BTN_BACK,
    BTN_CLAN,
    BTN_DECK,
    BTN_DONATE,
    BTN_PASS,
    BTN_PROFILE,
    BTN_QUESTS,
    BTN_SETTINGS,
    BTN_SHOP,
)


def main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text=BTN_PROFILE), KeyboardButton(text=BTN_DECK), KeyboardButton(text=BTN_SHOP)],
        [KeyboardButton(text=BTN_CLAN), KeyboardButton(text=BTN_PASS), KeyboardButton(text=BTN_DONATE)],
        [KeyboardButton(text=BTN_QUESTS), KeyboardButton(text=BTN_SETTINGS)],
    ]
    # is_persistent=False (по явной просьбе пользователя 2026-08-06, см. CLAUDE.md) — даёт
    # клиенту Telegram показать стандартную стрелку сворачивания клавиатуры рядом с полем
    # ввода. is_persistent=True форсит клавиатуру всегда открытой без возможности свернуть.
    # selective=True (2026-08-15) — в группе клавиатура иначе одна на весь чат: показывается
    # ВСЕМ участникам и заменяется, стоит боту прислать её кому угодно ещё, из-за чего игроки
    # путали чужие кнопки со своими. С selective=True Telegram показывает её только тому, чьё
    # сообщение бот реплаит (см. вызовы .reply(...) вместо .answer(...) в handlers/start) —
    # в личных чатах эффекта не даёт (там и так один пользователь).
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=False, selective=True)


def back_button_menu(callback_data: str) -> InlineKeyboardMarkup:
    """Общая клавиатура из одной кнопки "◀️ Назад" — вешается на экраны "ожидания ввода"
    (вместо текстовой подсказки "/cancel — отменить.", см. CLAUDE.md, 2026-08-21): игрок
    жмёт кнопку и возвращается на предыдущий экран, а не вспоминает команду. `callback_data`
    — это ВСЕГДА уже существующий в проекте callback, который открывает нужный "предыдущий"
    экран (и, если нужно, сам чистит FSM-состояние) — здесь не заводится новой логики
    рендера, только переиспользование."""
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=callback_data)]])
