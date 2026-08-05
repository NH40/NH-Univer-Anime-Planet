from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.deck import (
    CB_DECK_CHANCES,
    CB_DECK_COLLECTION,
    CB_DECK_OPEN,
    CB_DECK_ROLL1,
    CB_DECK_ROLL10,
)
from bot.texts.common import BTN_BACK
from bot.texts.deck import (
    BTN_CHANCES,
    BTN_COLLECTION,
    BTN_DISENCHANT,
    BTN_MERGE,
    BTN_ROLL_1,
    BTN_ROLL_10,
)


def deck_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
    )


def back_to_deck() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)]])
