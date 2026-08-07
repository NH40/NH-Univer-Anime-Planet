from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.settings import get_settings
from bot.constant.battle_pass import (
    CB_BATTLE_PASS_CLAIM_FREE,
    CB_BATTLE_PASS_CLAIM_PREMIUM,
    CB_BATTLE_PASS_OPEN,
    LOCK_ACTION_CLAIM_PASS_FREE,
    LOCK_ACTION_CLAIM_PASS_PREMIUM,
)
from bot.db.repositories.user import get_by_id
from bot.keyboards.battle_pass import pass_menu
from bot.services import battle_pass as pass_service
from bot.texts.battle_pass import (
    PASS_CLAIM_FREE_DONE,
    PASS_CLAIM_NONE,
    PASS_CLAIM_NOT_PREMIUM,
    PASS_CLAIM_PREMIUM_DONE,
    PASS_NO_SEASON,
    PASS_PREMIUM_ACTIVE,
    PASS_PREMIUM_LOCKED,
    PASS_PROGRESS_LINE,
    PASS_REWARD_LOCKED,
    PASS_REWARD_NONE,
    PASS_REWARD_PENDING,
    PASS_REWARD_PENDING_PREMIUM,
    PASS_SCREEN,
)
from bot.texts.common import BTN_PASS, NEED_START
from bot.utils.formatting import progress_bar
from bot.utils.safe_edit import safe_edit_text

router = Router(name="battle_pass")


def _render(view: pass_service.PassView, *, mini_app_url: str | None) -> tuple[str, InlineKeyboardMarkup]:
    have = view.progress - view.progress_level_floor
    need = view.progress_next_level_ceiling - view.progress_level_floor
    percent = round(100 * have / need) if need else 100
    progress = PASS_PROGRESS_LINE.format(percent=percent, have=have, need=need)

    if view.pending_free_dust or view.pending_free_tickets:
        free_line = PASS_REWARD_PENDING.format(dust=view.pending_free_dust, tickets=view.pending_free_tickets)
    else:
        free_line = PASS_REWARD_NONE

    if not view.is_premium:
        premium_line = PASS_REWARD_LOCKED
    elif view.pending_premium_dust or view.pending_premium_tickets or view.pending_premium_coins:
        premium_line = PASS_REWARD_PENDING_PREMIUM.format(
            dust=view.pending_premium_dust, tickets=view.pending_premium_tickets, coins=view.pending_premium_coins
        )
    else:
        premium_line = PASS_REWARD_NONE

    text = PASS_SCREEN.format(
        level=view.level,
        bar=progress_bar(percent),
        progress=progress,
        free_line=free_line,
        premium_emoji="💎" if view.is_premium else "🔒",
        premium_status=PASS_PREMIUM_ACTIVE if view.is_premium else PASS_PREMIUM_LOCKED,
        premium_line=premium_line,
    )
    keyboard = pass_menu(
        free_claimable=view.free_claimable,
        premium_claimable=view.premium_claimable,
        is_premium=view.is_premium,
        mini_app_url=mini_app_url,
    )
    return text, keyboard


async def _show(session: AsyncSession, user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    view = await pass_service.get_pass_view(session, user_id=user_id)
    if view is None:
        return None
    settings = get_settings()
    return _render(view, mini_app_url=settings.mini_app_url or None)


@router.message(Command("pass"))
@router.message(F.text == BTN_PASS)
async def show_pass(message: Message, session: AsyncSession) -> None:
    user = await get_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return

    result = await _show(session, message.from_user.id)
    if result is None:
        await message.answer(PASS_NO_SEASON)
        return
    text, keyboard = result
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == CB_BATTLE_PASS_OPEN)
async def cb_open_pass(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    result = await _show(session, callback.from_user.id)
    if result is None:
        await safe_edit_text(callback.message, PASS_NO_SEASON)
        return
    text, keyboard = result
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == CB_BATTLE_PASS_CLAIM_FREE)
async def cb_claim_free(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CLAIM_PASS_FREE)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            dust, tickets = await pass_service.claim_free(session, user_id=user_id)
        except pass_service.NoSeasonActiveError:
            await callback.answer(PASS_NO_SEASON, show_alert=True)
            return
        except pass_service.NothingToClaimError:
            await callback.answer(PASS_CLAIM_NONE, show_alert=True)
            return
        await callback.answer(PASS_CLAIM_FREE_DONE.format(dust=dust, tickets=tickets), show_alert=True)

    result = await _show(session, user_id)
    if result is not None:
        text, keyboard = result
        await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == CB_BATTLE_PASS_CLAIM_PREMIUM)
async def cb_claim_premium(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CLAIM_PASS_PREMIUM)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            dust, tickets, coins = await pass_service.claim_premium(session, user_id=user_id)
        except pass_service.NoSeasonActiveError:
            await callback.answer(PASS_NO_SEASON, show_alert=True)
            return
        except pass_service.NotPremiumError:
            await callback.answer(PASS_CLAIM_NOT_PREMIUM, show_alert=True)
            return
        except pass_service.NothingToClaimError:
            await callback.answer(PASS_CLAIM_NONE, show_alert=True)
            return
        await callback.answer(PASS_CLAIM_PREMIUM_DONE.format(dust=dust, tickets=tickets, coins=coins), show_alert=True)

    result = await _show(session, user_id)
    if result is not None:
        text, keyboard = result
        await safe_edit_text(callback.message, text, reply_markup=keyboard)
