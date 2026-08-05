from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.constant.profile import (
    CB_PLAYERS_PAGE_PREFIX,
    CB_PROFILE_DAILY_BONUS,
    CB_PROFILE_REFERRALS,
    CB_PROFILE_RENAME,
)
from bot.texts.common import BTN_PROFILE_APP
from bot.texts.profile import BTN_DAILY_BONUS, BTN_REFERRALS, BTN_RENAME


def profile_menu(*, mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=BTN_RENAME, callback_data=CB_PROFILE_RENAME)],
        [
            InlineKeyboardButton(text=BTN_REFERRALS, callback_data=CB_PROFILE_REFERRALS),
            InlineKeyboardButton(text=BTN_DAILY_BONUS, callback_data=CB_PROFILE_DAILY_BONUS),
        ],
    ]
    if mini_app_url:
        # ?view=profile — src/web/src/App.tsx читает это при загрузке и открывает
        # страницу профиля с прогрессом вместо коллекции по умолчанию.
        rows.append(
            [InlineKeyboardButton(text=BTN_PROFILE_APP, web_app=WebAppInfo(url=f"{mini_app_url}?view=profile"))]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def players_pager(page: int, total_pages: int) -> InlineKeyboardMarkup:
    buttons = []
    if page > 0:
        buttons.append(
            InlineKeyboardButton(text="« Назад", callback_data=f"{CB_PLAYERS_PAGE_PREFIX}{page - 1}")
        )
    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(text="Вперёд »", callback_data=f"{CB_PLAYERS_PAGE_PREFIX}{page + 1}")
        )
    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])
