from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.clan import CB_CLAN_EXCHANGE_START, LOCK_ACTION_EXCHANGE_DUST
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_username as get_user_by_username
from bot.services import clan as clan_service
from bot.states.clan import ClanStates
from bot.texts.clan import (
    ACTION_CANCELLED,
    EXCHANGE_DONE,
    EXCHANGE_INVALID,
    EXCHANGE_NOT_ENOUGH_DUST,
    EXCHANGE_NOT_IN_CLAN,
    EXCHANGE_PROMPT,
    INVITE_USER_NOT_FOUND,
    NOTIFY_EXCHANGE_RECEIVED,
    NOT_IN_CLAN,
)
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_exchange")


@router.callback_query(F.data == CB_CLAN_EXCHANGE_START)
async def cb_exchange_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return
    await state.set_state(ClanStates.waiting_exchange_input)
    await callback.answer()
    await safe_edit_text(callback.message, EXCHANGE_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(ClanStates.waiting_exchange_input), Command("cancel"))
async def cancel_exchange(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_exchange_input))
async def apply_exchange(message: Message, state: FSMContext, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    parts = (message.text or "").strip().split()
    if len(parts) != 2 or not parts[0].startswith("@") or not parts[1].isdigit() or int(parts[1]) <= 0:
        await message.answer(EXCHANGE_INVALID)
        return

    username = parts[0].lstrip("@")
    amount = int(parts[1])
    await state.clear()

    sender_id = message.from_user.id
    target = await get_user_by_username(session, username)
    if target is None:
        await message.answer(INVITE_USER_NOT_FOUND)
        return

    async with try_acquire(redis, action_lock(sender_id, LOCK_ACTION_EXCHANGE_DUST)) as acquired:
        if not acquired:
            return

        try:
            await clan_service.exchange_dust(session, sender_id=sender_id, receiver_id=target.id, amount=amount)
        except clan_service.NotInSameClanError:
            await message.answer(EXCHANGE_NOT_IN_CLAN)
            return
        except clan_service.ExchangeNotEnoughDustError as exc:
            await message.answer(EXCHANGE_NOT_ENOUGH_DUST.format(needed=exc.needed))
            return

    display_username = target.username or str(target.id)
    await message.answer(EXCHANGE_DONE.format(amount=amount, username=display_username))

    if target.notifications_enabled:
        sender_username = message.from_user.username or str(sender_id)
        await notify(bot, target.id, NOTIFY_EXCHANGE_RECEIVED.format(amount=amount, username=sender_username))
