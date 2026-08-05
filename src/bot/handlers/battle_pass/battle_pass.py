from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import BATTLE_PASS_MAX_LEVEL
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
    PASS_MAX_LEVEL_LINE,
    PASS_NO_SEASON,
    PASS_PREMIUM_ACTIVE,
    PASS_PREMIUM_LOCKED,
    PASS_PROGRESS_LINE,
    PASS_SCREEN,
)
from bot.texts.common import BTN_PASS, NEED_START
from bot.utils.safe_edit import safe_edit_text

router = Router(name="battle_pass")


def _render(view: pass_service.PassView) -> tuple[str, InlineKeyboardMarkup]:
    if view.ubp_next_level_ceiling is None:
        progress = PASS_MAX_LEVEL_LINE
    else:
        have = view.ubp_season - view.ubp_level_floor
        need = view.ubp_next_level_ceiling - view.ubp_level_floor
        progress = PASS_PROGRESS_LINE.format(have=have, need=need)

    premium_status = PASS_PREMIUM_ACTIVE if view.is_premium else PASS_PREMIUM_LOCKED
    text = PASS_SCREEN.format(
        level=view.level,
        max_level=BATTLE_PASS_MAX_LEVEL,
        progress=progress,
        ubp_season=view.ubp_season,
        premium_status=premium_status,
    )
    keyboard = pass_menu(
        free_claimable=view.free_claimable, premium_claimable=view.premium_claimable, is_premium=view.is_premium
    )
    return text, keyboard


async def _show(session: AsyncSession, user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    view = await pass_service.get_pass_view(session, user_id=user_id)
    if view is None:
        return None
    return _render(view)


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
