from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.battle_pass import (
    CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX,
    CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX,
    CB_BATTLE_PASS_LEVELS_PAGE_PREFIX,
    LOCK_ACTION_CLAIM_PASS_FREE,
    LOCK_ACTION_CLAIM_PASS_PREMIUM,
)
from bot.keyboards.battle_pass import levels_menu
from bot.services import battle_pass as pass_service
from bot.texts.battle_pass import (
    PASS_CLAIM_NONE,
    PASS_LEVEL_COINS_PART,
    PASS_LEVEL_ICON_CLAIMED,
    PASS_LEVEL_ICON_LOCKED,
    PASS_LEVEL_ICON_READY,
    PASS_LEVEL_LINE,
    PASS_LEVEL_TICKETS_PART,
    PASS_LEVELS_NO_SEASON,
    PASS_LEVELS_TITLE,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="battle_pass_levels")


def _render(page_view: pass_service.LevelsPage) -> tuple[str, InlineKeyboardMarkup]:
    lines = [
        PASS_LEVELS_TITLE.format(
            page=page_view.page, total_pages=page_view.total_pages, current_level=page_view.current_level
        )
    ]
    free_claimable = premium_claimable = False
    for entry in page_view.entries:
        if not entry.unlocked:
            icon = PASS_LEVEL_ICON_LOCKED
        elif (not entry.free_claimed) or (page_view.is_premium and not entry.premium_claimed):
            icon = PASS_LEVEL_ICON_READY
        else:
            icon = PASS_LEVEL_ICON_CLAIMED

        if entry.unlocked and not entry.free_claimed:
            free_claimable = True
        if entry.unlocked and page_view.is_premium and not entry.premium_claimed:
            premium_claimable = True

        free_tickets = PASS_LEVEL_TICKETS_PART.format(tickets=entry.free_tickets) if entry.free_tickets else ""
        premium_tickets = PASS_LEVEL_TICKETS_PART.format(tickets=entry.premium_tickets) if entry.premium_tickets else ""
        premium_coins = PASS_LEVEL_COINS_PART.format(coins=entry.premium_coins) if entry.premium_coins else ""
        lines.append(
            PASS_LEVEL_LINE.format(
                icon=icon,
                level=entry.level,
                free_dust=entry.free_dust,
                free_tickets=free_tickets,
                premium_dust=entry.premium_dust,
                premium_tickets=premium_tickets,
                premium_coins=premium_coins,
            )
        )

    text = "".join(lines)
    keyboard = levels_menu(
        page=page_view.page,
        total_pages=page_view.total_pages,
        free_claimable=free_claimable,
        premium_claimable=premium_claimable,
    )
    return text, keyboard


def _parse_page(data: str, prefix: str) -> int:
    try:
        return int(data[len(prefix) :])
    except ValueError:
        return 1


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_PAGE_PREFIX))
async def cb_open_levels(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    page = _parse_page(callback.data, CB_BATTLE_PASS_LEVELS_PAGE_PREFIX)
    page_view = await pass_service.list_levels(session, user_id=callback.from_user.id, page=page)
    if page_view is None:
        await safe_edit_text(callback.message, PASS_LEVELS_NO_SEASON)
        return
    text, keyboard = _render(page_view)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX))
async def cb_levels_claim_free(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    page = _parse_page(callback.data, CB_BATTLE_PASS_LEVELS_CLAIM_FREE_PREFIX)
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CLAIM_PASS_FREE)) as acquired:
        if not acquired:
            await callback.answer()
            return
        try:
            await pass_service.claim_free(session, user_id=user_id)
        except (pass_service.NoSeasonActiveError, pass_service.NothingToClaimError):
            await callback.answer(PASS_CLAIM_NONE, show_alert=True)
            return
        await callback.answer()

    page_view = await pass_service.list_levels(session, user_id=user_id, page=page)
    if page_view is not None:
        text, keyboard = _render(page_view)
        await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX))
async def cb_levels_claim_premium(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    page = _parse_page(callback.data, CB_BATTLE_PASS_LEVELS_CLAIM_PREMIUM_PREFIX)
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CLAIM_PASS_PREMIUM)) as acquired:
        if not acquired:
            await callback.answer()
            return
        try:
            await pass_service.claim_premium(session, user_id=user_id)
        except (
            pass_service.NoSeasonActiveError,
            pass_service.NotPremiumError,
            pass_service.NothingToClaimError,
        ):
            await callback.answer(PASS_CLAIM_NONE, show_alert=True)
            return
        await callback.answer()

    page_view = await pass_service.list_levels(session, user_id=user_id, page=page)
    if page_view is not None:
        text, keyboard = _render(page_view)
        await safe_edit_text(callback.message, text, reply_markup=keyboard)
