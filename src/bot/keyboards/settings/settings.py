from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.constant.settings import (
    CB_SET_UNIVERSE_PREFIX,
    CB_SETTINGS_NOTIFICATIONS_OPEN,
    CB_SETTINGS_OPEN,
    CB_SETTINGS_TOGGLE_CLAN_REQUESTS,
    CB_SETTINGS_TOGGLE_DAILY_BONUS,
    CB_SETTINGS_TOGGLE_DAILY_QUESTS,
    CB_SETTINGS_TOGGLE_ROLL_REMINDER,
    CB_SETTINGS_TOGGLE_TICKETS_FULL,
    CB_SETTINGS_UNIVERSE_OPEN,
)
from bot.db.models.universe import Universe
from bot.texts.common import BTN_BACK
from bot.texts.settings import (
    BTN_NOTIFY_CLAN_REQUESTS,
    BTN_NOTIFY_DAILY_BONUS,
    BTN_NOTIFY_DAILY_QUESTS,
    BTN_NOTIFY_ROLL_REMINDER,
    BTN_NOTIFY_TICKETS_FULL,
    BTN_SETTINGS_NOTIFICATIONS,
    BTN_SETTINGS_UNIVERSE,
    STATUS_OFF,
    STATUS_ON,
)


def settings_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BTN_SETTINGS_UNIVERSE, callback_data=CB_SETTINGS_UNIVERSE_OPEN)],
            [InlineKeyboardButton(text=BTN_SETTINGS_NOTIFICATIONS, callback_data=CB_SETTINGS_NOTIFICATIONS_OPEN)],
        ]
    )


def universe_picker(universes: list[Universe]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=u.title, callback_data=f"{CB_SET_UNIVERSE_PREFIX}{u.code}")]
        for u in universes
    ]
    rows.append([InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SETTINGS_OPEN)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def notifications_menu(
    *, tickets_full: bool, roll_reminder: bool, clan_requests: bool, daily_bonus: bool, daily_quests: bool
) -> InlineKeyboardMarkup:
    tickets_full_status = STATUS_ON if tickets_full else STATUS_OFF
    roll_reminder_status = STATUS_ON if roll_reminder else STATUS_OFF
    clan_requests_status = STATUS_ON if clan_requests else STATUS_OFF
    daily_bonus_status = STATUS_ON if daily_bonus else STATUS_OFF
    daily_quests_status = STATUS_ON if daily_quests else STATUS_OFF
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BTN_NOTIFY_TICKETS_FULL.format(status=tickets_full_status),
                    callback_data=CB_SETTINGS_TOGGLE_TICKETS_FULL,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_NOTIFY_ROLL_REMINDER.format(status=roll_reminder_status),
                    callback_data=CB_SETTINGS_TOGGLE_ROLL_REMINDER,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_NOTIFY_CLAN_REQUESTS.format(status=clan_requests_status),
                    callback_data=CB_SETTINGS_TOGGLE_CLAN_REQUESTS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_NOTIFY_DAILY_BONUS.format(status=daily_bonus_status),
                    callback_data=CB_SETTINGS_TOGGLE_DAILY_BONUS,
                )
            ],
            [
                InlineKeyboardButton(
                    text=BTN_NOTIFY_DAILY_QUESTS.format(status=daily_quests_status),
                    callback_data=CB_SETTINGS_TOGGLE_DAILY_QUESTS,
                )
            ],
            [InlineKeyboardButton(text=BTN_BACK, callback_data=CB_SETTINGS_OPEN)],
        ]
    )
