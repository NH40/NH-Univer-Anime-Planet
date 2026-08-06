from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.admin import (
    CB_ADMIN_BROADCAST_CONFIRM,
    CB_ADMIN_BROADCAST_START,
    CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX,
    CB_ADMIN_DELETE_ACCOUNT_START,
    CB_ADMIN_EVENT_TOGGLE_PREFIX,
    CB_ADMIN_EVENTS,
    CB_ADMIN_FIND_PLAYER_START,
    CB_ADMIN_MANAGE_ADMINS,
    CB_ADMIN_MANAGE_FIND_PLAYER,
    CB_ADMIN_MASS_GRANT,
    CB_ADMIN_MASS_GRANT_CONFIRM,
    CB_ADMIN_MASS_GRANT_COINS,
    CB_ADMIN_MASS_GRANT_DUST,
    CB_ADMIN_MASS_GRANT_TICKETS,
    CB_ADMIN_OPEN,
    CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX,
    CB_ADMIN_PLAYER_GIVE_CARD_PREFIX,
    CB_ADMIN_PLAYER_GIVE_COINS_PREFIX,
    CB_ADMIN_PLAYER_GIVE_DUST_PREFIX,
    CB_ADMIN_PROMO,
    CB_ADMIN_PROMO_CREATE,
    CB_ADMIN_REFERRAL,
    CB_ADMIN_REFERRAL_CREATE,
    CB_ADMIN_REFERRAL_DETAIL_PREFIX,
    CB_ADMIN_SEASON,
    CB_ADMIN_SEASON_BUMP_VERSION,
    CB_ADMIN_SEASON_NEW,
    CB_ADMIN_SEASON_NEW_CONFIRM,
    CB_ADMIN_STATS,
    CB_ADMIN_TECH_MODE_TOGGLE,
    CB_ADMIN_TOGGLE_ADMIN_PREFIX,
    CB_ADMIN_WIPE_CONFIRM,
    CB_ADMIN_WIPE_START,
)
from bot.texts.admin import (
    BTN_ADMIN_BROADCAST,
    BTN_ADMIN_DELETE_ACCOUNT,
    BTN_ADMIN_EVENTS,
    BTN_ADMIN_FIND_PLAYER,
    BTN_ADMIN_MANAGE_ADMINS,
    BTN_ADMIN_MASS_GRANT,
    BTN_ADMIN_PROMO,
    BTN_ADMIN_REFERRAL,
    BTN_ADMIN_SEASON,
    BTN_ADMIN_STATS,
    BTN_ADMIN_TECH_MODE,
    BTN_ADMIN_WIPE,
    BTN_BAN,
    BTN_CONFIRM,
    BTN_EVENT_ACTIVATE_PREFIX,
    BTN_EVENT_DEACTIVATE_PREFIX,
    BTN_FIND_ANOTHER,
    BTN_GIVE_CARD,
    BTN_GIVE_COINS,
    BTN_GIVE_DUST,
    BTN_GRANT_ADMIN,
    BTN_MANAGE_FIND_PLAYER,
    BTN_MASS_GRANT_COINS,
    BTN_MASS_GRANT_DUST,
    BTN_MASS_GRANT_TICKETS,
    BTN_PROMO_CREATE,
    BTN_REFERRAL_CREATE,
    BTN_REVOKE_ADMIN,
    BTN_SEASON_BUMP_VERSION,
    BTN_SEASON_NEW,
    BTN_UNBAN,
)
from bot.services.event import EventStatus
from bot.texts.common import BTN_BACK
from bot.texts.settings import STATUS_OFF, STATUS_ON


def admin_menu(*, tech_mode_enabled: bool, is_super_admin: bool = False) -> InlineKeyboardMarkup:
    status = STATUS_ON if tech_mode_enabled else STATUS_OFF
    rows = [
        # Техрежим — отдельной строкой на всю ширину: единственная кнопка с динамическим
        # статусом в тексте, остальные — по 2 в строке для компактности.
        [InlineKeyboardButton(text=BTN_ADMIN_TECH_MODE.format(status=status), callback_data=CB_ADMIN_TECH_MODE_TOGGLE)],
        [
            InlineKeyboardButton(text=BTN_ADMIN_STATS, callback_data=CB_ADMIN_STATS),
            InlineKeyboardButton(text=BTN_ADMIN_FIND_PLAYER, callback_data=CB_ADMIN_FIND_PLAYER_START),
        ],
        [
            InlineKeyboardButton(text=BTN_ADMIN_SEASON, callback_data=CB_ADMIN_SEASON),
            InlineKeyboardButton(text=BTN_ADMIN_PROMO, callback_data=CB_ADMIN_PROMO),
        ],
        [
            InlineKeyboardButton(text=BTN_ADMIN_REFERRAL, callback_data=CB_ADMIN_REFERRAL),
            InlineKeyboardButton(text=BTN_ADMIN_BROADCAST, callback_data=CB_ADMIN_BROADCAST_START),
        ],
        [
            InlineKeyboardButton(text=BTN_ADMIN_MASS_GRANT, callback_data=CB_ADMIN_MASS_GRANT),
            InlineKeyboardButton(text=BTN_ADMIN_DELETE_ACCOUNT, callback_data=CB_ADMIN_DELETE_ACCOUNT_START),
        ],
        # Ивенты — контентная функция, не деструктивная, доступна ЛЮБОМУ админу, не
        # только супер-админу (в отличие от блока ниже).
        [InlineKeyboardButton(text=BTN_ADMIN_EVENTS, callback_data=CB_ADMIN_EVENTS)],
    ]
    if is_super_admin:
        # Управление правами и полный сброс БД доступны ТОЛЬКО супер-админам (ADMIN_IDS из
        # .env) — обычные доп.админы (User.is_admin) даже не видят эти кнопки, тот же принцип
        # "не палить лишнее", что у всего /admin (см. CLAUDE.md, "Админ-панель").
        rows.append([InlineKeyboardButton(text=BTN_ADMIN_MANAGE_ADMINS, callback_data=CB_ADMIN_MANAGE_ADMINS)])
        rows.append([InlineKeyboardButton(text=BTN_ADMIN_WIPE, callback_data=CB_ADMIN_WIPE_START)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)]])


def manage_admins_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_MANAGE_FIND_PLAYER, callback_data=CB_ADMIN_MANAGE_FIND_PLAYER)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def manage_admin_card_menu(*, user_id: int, is_admin: bool) -> InlineKeyboardMarkup:
    toggle_button = InlineKeyboardButton(
        text=BTN_REVOKE_ADMIN if is_admin else BTN_GRANT_ADMIN,
        callback_data=f"{CB_ADMIN_TOGGLE_ADMIN_PREFIX}{user_id}",
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [toggle_button],
            [InlineKeyboardButton(text=BTN_MANAGE_FIND_PLAYER, callback_data=CB_ADMIN_MANAGE_FIND_PLAYER)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_MANAGE_ADMINS)],
        ]
    )


def player_card_menu(*, user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    ban_button = InlineKeyboardButton(
        text=BTN_UNBAN if is_banned else BTN_BAN, callback_data=f"{CB_ADMIN_PLAYER_BAN_TOGGLE_PREFIX}{user_id}"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_GIVE_DUST, callback_data=f"{CB_ADMIN_PLAYER_GIVE_DUST_PREFIX}{user_id}")],
            [InlineKeyboardButton(text=BTN_GIVE_COINS, callback_data=f"{CB_ADMIN_PLAYER_GIVE_COINS_PREFIX}{user_id}")],
            [InlineKeyboardButton(text=BTN_GIVE_CARD, callback_data=f"{CB_ADMIN_PLAYER_GIVE_CARD_PREFIX}{user_id}")],
            [ban_button],
            [InlineKeyboardButton(text=BTN_FIND_ANOTHER, callback_data=CB_ADMIN_FIND_PLAYER_START)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def season_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_SEASON_NEW, callback_data=CB_ADMIN_SEASON_NEW)],
            [InlineKeyboardButton(text=BTN_SEASON_BUMP_VERSION, callback_data=CB_ADMIN_SEASON_BUMP_VERSION)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def season_new_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONFIRM, callback_data=CB_ADMIN_SEASON_NEW_CONFIRM)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_SEASON)],
        ]
    )


def promo_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_PROMO_CREATE, callback_data=CB_ADMIN_PROMO_CREATE)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def promo_create_prompt_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_PROMO)]])


def referral_menu(codes: list[str]) -> InlineKeyboardMarkup:
    """Кнопка на каждую именную кампанию (по названию) — тап открывает детальную
    статистику (см. handlers/admin/referral: cb_referral_detail), а не сваливает все
    цифры сразу одним текстом."""
    rows = [
        [InlineKeyboardButton(text=code, callback_data=f"{CB_ADMIN_REFERRAL_DETAIL_PREFIX}{code}")]
        for code in codes
    ]
    rows.append([InlineKeyboardButton(text=BTN_REFERRAL_CREATE, callback_data=CB_ADMIN_REFERRAL_CREATE)])
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def referral_detail_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_REFERRAL)]]
    )


def broadcast_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONFIRM, callback_data=CB_ADMIN_BROADCAST_CONFIRM)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def mass_grant_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_MASS_GRANT_DUST, callback_data=CB_ADMIN_MASS_GRANT_DUST)],
            [InlineKeyboardButton(text=BTN_MASS_GRANT_COINS, callback_data=CB_ADMIN_MASS_GRANT_COINS)],
            [InlineKeyboardButton(text=BTN_MASS_GRANT_TICKETS, callback_data=CB_ADMIN_MASS_GRANT_TICKETS)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def mass_grant_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONFIRM, callback_data=CB_ADMIN_MASS_GRANT_CONFIRM)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_MASS_GRANT)],
        ]
    )


def delete_account_confirm_menu(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONFIRM, callback_data=f"{CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX}{user_id}")],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )


def events_menu(statuses: list[EventStatus]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{BTN_EVENT_DEACTIVATE_PREFIX if s.is_active else BTN_EVENT_ACTIVATE_PREFIX}{s.title}",
                callback_data=f"{CB_ADMIN_EVENT_TOGGLE_PREFIX}{s.code}",
            )
        ]
        for s in statuses
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def wipe_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_CONFIRM, callback_data=CB_ADMIN_WIPE_CONFIRM)],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_ADMIN_OPEN)],
        ]
    )
