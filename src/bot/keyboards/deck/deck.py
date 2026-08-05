from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.constant.deck import (
    CB_DECK_CHANCES,
    CB_DECK_COLLECTION,
    CB_DECK_OPEN,
    CB_DECK_ROLL1,
    CB_DECK_ROLL10,
)
from bot.texts.common import BTN_BACK, BTN_COLLECTION_APP
from bot.texts.deck import (
    BTN_CHANCES,
    BTN_COLLECTION,
    BTN_DISENCHANT,
    BTN_MERGE,
    BTN_ROLL_1,
    BTN_ROLL_10,
)


def deck_menu(*, mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=BTN_ROLL_1, callback_data=CB_DECK_ROLL1),
            InlineKeyboardButton(text=BTN_ROLL_10, callback_data=CB_DECK_ROLL10),
        ],
        [
            InlineKeyboardButton(text=BTN_COLLECTION, callback_data=CB_DECK_COLLECTION),
            InlineKeyboardButton(text=BTN_CHANCES, callback_data=CB_DECK_CHANCES),
        ],
        [
            # Распыление и слияние живут внутри "Коллекции" (выбор конкретной стопки
            # карт), а не отдельными плоскими флоу — см. handlers/collection.
            InlineKeyboardButton(text=BTN_DISENCHANT, callback_data=CB_DECK_COLLECTION),
            InlineKeyboardButton(text=BTN_MERGE, callback_data=CB_DECK_COLLECTION),
        ],
    ]
    if mini_app_url:
        # Mini App показывает ВСЮ коллекцию игрока сразу (по всем вселенным, см. CLAUDE.md,
        # "Mini App" -> /api/universes), в отличие от BTN_COLLECTION выше (только текущая
        # выбранная вселенная) — поэтому это отдельная кнопка, не замена. Живёт здесь, а не
        # в главном reply-меню (см. CLAUDE.md/TODO) — доступна в контексте экрана "Колода",
        # не занимает постоянное место в меню. Кнопка есть только когда настроен домен/HTTPS.
        rows.append([InlineKeyboardButton(text=BTN_COLLECTION_APP, web_app=WebAppInfo(url=mini_app_url))])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_deck() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)]])
