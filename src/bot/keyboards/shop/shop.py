from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.config.game import (
    SHOP_TICKET_PRESETS,
    TICKET_CAP_SLOT_PRESETS,
    TICKET_CAP_SLOT_PRICE_PERMANENT_COINS,
    TICKET_CAP_SLOT_PRICE_SEASONAL_COINS,
)
from bot.constant.casino import CB_CASINO_OPEN
from bot.constant.shop import (
    CB_COINSHOP_BATTLE_PASS,
    CB_COINSHOP_BATTLE_PASS_CONFIRM,
    CB_COINSHOP_CANCEL,
    CB_COINSHOP_PACKS,
    CB_COINSHOP_SUBSCRIPTION,
    CB_COINSHOP_SUBSCRIPTION_CONFIRM,
    CB_COINSHOP_TICKET_CAP,
    CB_COINSHOP_TICKET_CAP_ASK_PREFIX,
    CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX,
    CB_COINSHOP_TICKET_CAP_PERMANENT,
    CB_COINSHOP_TICKET_CAP_SEASONAL,
    CB_COINSHOP_TICKETS,
    CB_COINSHOP_TICKETS_CONFIRM,
    CB_SHOP_BUY_TICKETS_CUSTOM,
    CB_SHOP_BUY_TICKETS_MAX,
    CB_SHOP_BUY_TICKETS_PREFIX,
    CB_SHOP_COINS,
    CB_SHOP_DUST,
    CB_SHOP_OPEN,
)
from bot.texts.common import BTN_BACK
from bot.texts.shop import (
    BTN_BATTLE_PASS,
    BTN_BUY_BATTLE_PASS,
    BTN_BUY_MAX,
    BTN_BUY_SUBSCRIPTION,
    BTN_CANCEL,
    BTN_CASINO,
    BTN_COIN_TICKETS,
    BTN_CONFIRM,
    BTN_CUSTOM_QUANTITY,
    BTN_PACKS,
    BTN_SHOP_COINS,
    BTN_SHOP_DUST,
    BTN_SUBSCRIPTION,
    BTN_TICKET_CAP,
    BTN_TICKET_CAP_PERMANENT,
    BTN_TICKET_CAP_SEASONAL,
    BTN_TICKET_PRESET,
)


def shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_SHOP_DUST, callback_data=CB_SHOP_DUST)],
            [InlineKeyboardButton(text=BTN_SHOP_COINS, callback_data=CB_SHOP_COINS)],
        ]
    )


def dust_shop_menu() -> InlineKeyboardMarkup:
    presets_row = [
        InlineKeyboardButton(
            text=BTN_TICKET_PRESET.format(qty=qty), callback_data=f"{CB_SHOP_BUY_TICKETS_PREFIX}{qty}"
        )
        for qty in SHOP_TICKET_PRESETS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            presets_row,
            [
                InlineKeyboardButton(text=BTN_BUY_MAX, callback_data=CB_SHOP_BUY_TICKETS_MAX),
                InlineKeyboardButton(text=BTN_CUSTOM_QUANTITY, callback_data=CB_SHOP_BUY_TICKETS_CUSTOM),
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_OPEN)],
        ]
    )


def coin_shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_SUBSCRIPTION, callback_data=CB_COINSHOP_SUBSCRIPTION)],
            [InlineKeyboardButton(text=BTN_BATTLE_PASS, callback_data=CB_COINSHOP_BATTLE_PASS)],
            [InlineKeyboardButton(text=BTN_COIN_TICKETS, callback_data=CB_COINSHOP_TICKETS)],
            [InlineKeyboardButton(text=BTN_CASINO, callback_data=CB_CASINO_OPEN)],
            [InlineKeyboardButton(text=BTN_PACKS, callback_data=CB_COINSHOP_PACKS)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_OPEN)],
        ]
    )


def packs_menu() -> InlineKeyboardMarkup:
    """Список пак-типов — сейчас только "Макс хранилище", задел на будущие паки (см.
    CLAUDE.md) без переделки структуры меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_TICKET_CAP, callback_data=CB_COINSHOP_TICKET_CAP)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_COINS)],
        ]
    )


def subscription_menu(price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_BUY_SUBSCRIPTION.format(price=price), callback_data=CB_COINSHOP_SUBSCRIPTION_CONFIRM
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_COINS)],
        ]
    )


def battle_pass_menu(price: int, *, already_premium: bool) -> InlineKeyboardMarkup:
    rows = []
    if not already_premium:
        # Разовая покупка на сезон — если премиум уже открыт, повторно покупать нечего
        # (см. services/shop.buy_premium_pass), кнопку не показываем вовсе.
        rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_BUY_BATTLE_PASS.format(price=price), callback_data=CB_COINSHOP_BATTLE_PASS_CONFIRM
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SHOP_COINS)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_cancel_menu(confirm_callback: str) -> InlineKeyboardMarkup:
    """Общая клавиатура "подтвердить/отменить" для флоу с вводом числа (тикеты за коины,
    масс-крутка казино) — confirm_callback у каждого флоу свой, отмена — одна на всех."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=BTN_CONFIRM, callback_data=confirm_callback),
                InlineKeyboardButton(text=BTN_CANCEL, callback_data=CB_COINSHOP_CANCEL),
            ]
        ]
    )


def coin_tickets_confirm_menu() -> InlineKeyboardMarkup:
    return confirm_cancel_menu(CB_COINSHOP_TICKETS_CONFIRM)


def ticket_cap_menu() -> InlineKeyboardMarkup:
    """Seasonal/Permanent ведут на экран выбора количества (ticket_cap_quantity_menu), не
    покупают напрямую — см. CLAUDE.md, "Магазин: слот капа тикетов"."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_TICKET_CAP_SEASONAL.format(price=TICKET_CAP_SLOT_PRICE_SEASONAL_COINS),
                    callback_data=CB_COINSHOP_TICKET_CAP_SEASONAL,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_TICKET_CAP_PERMANENT.format(price=TICKET_CAP_SLOT_PRICE_PERMANENT_COINS),
                    callback_data=CB_COINSHOP_TICKET_CAP_PERMANENT,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_COINSHOP_PACKS)],
        ]
    )


def ticket_cap_quantity_menu(kind: str) -> InlineKeyboardMarkup:
    """Пресеты (TICKET_CAP_SLOT_PRESETS) + своё число — каждый ведёт на экран подтверждения
    (ASK), не покупает сразу (тот же принцип, что распыление, см. CLAUDE.md)."""
    presets_row = [
        InlineKeyboardButton(
            text=BTN_TICKET_PRESET.format(qty=qty), callback_data=f"{CB_COINSHOP_TICKET_CAP_ASK_PREFIX}{kind}:{qty}"
        )
        for qty in TICKET_CAP_SLOT_PRESETS
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            presets_row,
            [InlineKeyboardButton(text=BTN_CUSTOM_QUANTITY, callback_data=f"{CB_COINSHOP_TICKET_CAP_CUSTOM_PREFIX}{kind}")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_COINSHOP_TICKET_CAP)],
        ]
    )


def ticket_cap_ask_menu(confirm_callback: str) -> InlineKeyboardMarkup:
    return confirm_cancel_menu(confirm_callback)
