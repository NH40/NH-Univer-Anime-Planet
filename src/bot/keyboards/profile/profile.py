from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.constant.profile import (
    CB_PLAYERS_PAGE_PREFIX,
    CB_PROFILE_DAILY_BONUS,
    CB_PROFILE_OPEN,
    CB_PROFILE_REFERRALS,
    CB_PROFILE_RENAME,
    CB_TOP_PREFIX,
    TOP_SCOPE_SEASON,
    TOP_SCOPE_TOTAL,
)
from bot.db.models.universe import Universe
from bot.texts.common import BTN_BACK, BTN_PROFILE_APP
from bot.texts.profile import BTN_DAILY_BONUS, BTN_REFERRALS, BTN_RENAME, BTN_TOP_SCOPE_SEASON, BTN_TOP_SCOPE_TOTAL
from bot.utils.mini_app import mini_app_url as build_mini_app_url


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
        # страницу профиля с прогрессом вместо коллекции по умолчанию. ?v=... (см.
        # utils/mini_app) бампится вручную при деплое фронтенда, чтобы Telegram не отдавал
        # клиенту старый закэшированный index.html под тем же url.
        rows.append(
            [
                InlineKeyboardButton(
                    text=BTN_PROFILE_APP, web_app=WebAppInfo(url=build_mini_app_url(mini_app_url, view="profile"))
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_profile() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=BTN_BACK, callback_data=CB_PROFILE_OPEN)]])


def top_menu(universes: list[Universe], *, selected_universe: str, scope: str) -> InlineKeyboardMarkup:
    """Один экран с двумя независимыми селекторами (см. CLAUDE.md, "Топ по вселенной") —
    тап по вселенной или по периоду перерисовывает список, сохраняя ВТОРОЙ выбор как есть
    (оба закодированы в одном callback_data). Активная кнопка отмечена ✅, чтобы было видно
    текущий выбор без отдельного текста."""
    universe_row: list[InlineKeyboardButton] = []
    for universe in universes:
        label = f"✅ {universe.title}" if universe.code == selected_universe else universe.title
        universe_row.append(
            InlineKeyboardButton(text=label, callback_data=f"{CB_TOP_PREFIX}{universe.code}:{scope}")
        )

    season_label = f"✅ {BTN_TOP_SCOPE_SEASON}" if scope == TOP_SCOPE_SEASON else BTN_TOP_SCOPE_SEASON
    total_label = f"✅ {BTN_TOP_SCOPE_TOTAL}" if scope == TOP_SCOPE_TOTAL else BTN_TOP_SCOPE_TOTAL
    scope_row = [
        InlineKeyboardButton(text=season_label, callback_data=f"{CB_TOP_PREFIX}{selected_universe}:{TOP_SCOPE_SEASON}"),
        InlineKeyboardButton(text=total_label, callback_data=f"{CB_TOP_PREFIX}{selected_universe}:{TOP_SCOPE_TOTAL}"),
    ]

    # 2 вселенные в строке — при небольшом числе активных вселенных (сейчас 3) влезает без
    # переполнения ширины инлайн-клавиатуры Telegram; новые вселенные просто добавляют
    # ещё строки, без отдельного "другие вселенные"-подменю (см. CLAUDE.md).
    rows = [universe_row[i : i + 2] for i in range(0, len(universe_row), 2)]
    rows.append(scope_row)
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
