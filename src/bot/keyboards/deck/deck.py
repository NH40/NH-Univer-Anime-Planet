from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.config.game import TIER_CHANCE_PERCENT
from bot.constant.deck import (
    CB_DECK_CHANCES,
    CB_DECK_CHANCES_BACK,
    CB_DECK_CHANCES_TIER_PREFIX,
    CB_DECK_COLLECTION,
    CB_DECK_OPEN,
    CB_DECK_ROLL1,
)
from bot.db.models.card import Card
from bot.texts.common import BTN_BACK, BTN_COLLECTION_APP
from bot.texts.deck import (
    BTN_BACK_CHANCES,
    BTN_CHANCES,
    BTN_CHANCES_TIER,
    BTN_COLLECTION,
    BTN_DISENCHANT,
    BTN_MERGE,
    BTN_ROLL_1,
    BTN_ROLL_AGAIN,
    TIER_EMOJI,
    TIER_NAMES,
)


def deck_menu(*, mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BTN_ROLL_1, callback_data=CB_DECK_ROLL1)],
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


def roll_result_menu() -> InlineKeyboardMarkup:
    """Экран результата крутки — "Крутить ещё" сверху, в ТОМ ЖЕ месте на каждом новом
    сообщении (см. CLAUDE.md, "Крутка карточек": монотонный цикл "тап-тап-тап" без выхода
    в меню намеренно затягивает сильнее, чем пачка результатов x10). Переиспользует
    CB_DECK_ROLL1 — тот же callback, что и первая крутка с экрана "Колода"."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_ROLL_AGAIN, callback_data=CB_DECK_ROLL1)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)],
        ]
    )


def chances_menu(tier_map: dict[int, list[Card]]) -> InlineKeyboardMarkup:
    """Обзорный экран "Шансы" — по кнопке на тир (см. CLAUDE.md: цветной кружок + имя тира
    + % + число персонажей), клик открывает список персонажей этого тира (cb_chances_tier)."""
    rows = [
        [
            InlineKeyboardButton(
                text=BTN_CHANCES_TIER.format(
                    emoji=TIER_EMOJI[tier], name=TIER_NAMES[tier], chance=TIER_CHANCE_PERCENT[tier],
                    count=len(tier_map[tier]),
                ),
                callback_data=f"{CB_DECK_CHANCES_TIER_PREFIX}{tier}",
            )
        ]
        for tier in sorted(tier_map, reverse=True)
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_DECK_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def chances_tier_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK_CHANCES, callback_data=CB_DECK_CHANCES_BACK)]]
    )
