from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from bot.constant.battle_pass import (
    CB_BATTLE_PASS_CLAIM_ALL_FREE,
    CB_BATTLE_PASS_CLAIM_ALL_PREMIUM,
    CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX,
    CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX,
    CB_BATTLE_PASS_LEVELS_PAGE_PREFIX,
)
from bot.constant.shop import CB_COINSHOP_BATTLE_PASS
from bot.services.battle_pass import LevelEntry, LevelsPage
from bot.texts.battle_pass import (
    BTN_PASS_APP,
    BTN_PASS_BUY,
    BTN_PASS_CLAIM_ALL_FREE,
    BTN_PASS_CLAIM_ALL_PREMIUM,
    BTN_PASS_LEVEL_FREE,
    BTN_PASS_LEVEL_PREMIUM,
    BTN_PASS_PAGE_NEXT,
    BTN_PASS_PAGE_PREV,
    PASS_LEVEL_ICON_CLAIMED,
    PASS_LEVEL_ICON_LOCKED,
    PASS_LEVEL_REWARD_COINS_SUFFIX,
    PASS_LEVEL_REWARD_DUST,
    PASS_LEVEL_REWARD_TICKETS,
)


def _reward_text(dust: int, tickets: int, coins: int = 0) -> str:
    text = PASS_LEVEL_REWARD_TICKETS.format(tickets=tickets) if tickets else PASS_LEVEL_REWARD_DUST.format(dust=dust)
    if coins:
        text += PASS_LEVEL_REWARD_COINS_SUFFIX.format(coins=coins)
    return text


def _free_label(entry: LevelEntry) -> str:
    if not entry.unlocked:
        return f"{PASS_LEVEL_ICON_LOCKED} {entry.level}"
    if entry.free_claimed:
        return f"{PASS_LEVEL_ICON_CLAIMED} {entry.level}"
    return BTN_PASS_LEVEL_FREE.format(level=entry.level, reward=_reward_text(entry.free_dust, entry.free_tickets))


def _premium_label(entry: LevelEntry, *, is_premium: bool) -> str:
    if not is_premium:
        return f"{PASS_LEVEL_ICON_LOCKED}💎"
    if not entry.unlocked:
        return f"{PASS_LEVEL_ICON_LOCKED} {entry.level}"
    if entry.premium_claimed:
        return f"{PASS_LEVEL_ICON_CLAIMED} {entry.level}"
    reward = _reward_text(entry.premium_dust, entry.premium_tickets, entry.premium_coins)
    return BTN_PASS_LEVEL_PREMIUM.format(level=entry.level, reward=reward)


def levels_menu(page_view: LevelsPage, *, mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    """Сетка кнопок по уровням страницы — тап по ЛЮБОЙ доступной ячейке (в любом порядке,
    подтверждено пользователем 2026-08-11) забирает ТОЛЬКО её награду, см.
    CLAUDE.md, "Сезонный пасс: клейм произвольной ячейки". Кнопки заблокированных/уже
    забранных/недоступной премиум-ветки остаются кликабельными (Telegram не даёт по-другому
    "выключить" inline-кнопку) — тап по ним просто вернёт понятный alert от хендлера."""
    rows: list[list[InlineKeyboardButton]] = []

    for entry in page_view.entries:
        free_btn = InlineKeyboardButton(
            text=_free_label(entry),
            callback_data=f"{CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX}{page_view.page}:{entry.level}",
        )
        premium_btn = InlineKeyboardButton(
            text=_premium_label(entry, is_premium=page_view.is_premium),
            callback_data=f"{CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX}{page_view.page}:{entry.level}",
        )
        rows.append([free_btn, premium_btn])

    # "Забрать всё" зависит от high-water mark ветки целиком, а не от того, что видно на
    # ЭТОЙ странице (незабранные уровни могут лежать на другой странице) — см. docstring
    # LevelsPage.claimed_free_level/claimed_premium_level.
    any_free_claimable = page_view.claimed_free_level < page_view.current_level
    any_premium_claimable = page_view.is_premium and page_view.claimed_premium_level < page_view.current_level

    nav_row = []
    if page_view.page > 1:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PASS_PAGE_PREV, callback_data=f"{CB_BATTLE_PASS_LEVELS_PAGE_PREFIX}{page_view.page - 1}")
        )
    if page_view.page < page_view.total_pages:
        nav_row.append(
            InlineKeyboardButton(text=BTN_PASS_PAGE_NEXT, callback_data=f"{CB_BATTLE_PASS_LEVELS_PAGE_PREFIX}{page_view.page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    if any_free_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_ALL_FREE, callback_data=CB_BATTLE_PASS_CLAIM_ALL_FREE)])
    if any_premium_claimable:
        rows.append([InlineKeyboardButton(text=BTN_PASS_CLAIM_ALL_PREMIUM, callback_data=CB_BATTLE_PASS_CLAIM_ALL_PREMIUM)])
    if not page_view.is_premium:
        # Ведёт прямо в существующий экран покупки Battle Pass в магазине коинов
        # (handlers/shop) — не дублируем флоу оплаты здесь.
        rows.append([InlineKeyboardButton(text=BTN_PASS_BUY, callback_data=CB_COINSHOP_BATTLE_PASS)])
    if mini_app_url:
        # ?view=battlepass — src/web/src/App.tsx читает это при загрузке и сразу открывает
        # вкладку Battle Pass вместо коллекции по умолчанию.
        rows.append([InlineKeyboardButton(text=BTN_PASS_APP, web_app=WebAppInfo(url=f"{mini_app_url}?view=battlepass"))])

    return InlineKeyboardMarkup(inline_keyboard=rows)
