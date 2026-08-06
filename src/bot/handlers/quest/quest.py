from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.quest import DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT
from bot.constant.quest import (
    CB_QUEST_CLAIM_ALL,
    CB_QUEST_CLAIM_PREFIX,
    CB_QUEST_REROLL_ALL,
    CB_QUEST_REROLL_PREFIX,
    LOCK_ACTION_QUEST_CLAIM,
    LOCK_ACTION_QUEST_REROLL,
)
from bot.keyboards.quest import quests_menu
from bot.services import quest as quest_service
from bot.texts.common import BTN_QUESTS, NEED_START
from bot.texts.quest import (
    QUEST_ALREADY_CLAIMED,
    QUEST_CLAIM_ALL_DONE,
    QUEST_CLAIMED_DONE,
    QUEST_NOT_DONE,
    QUEST_NOTHING_TO_CLAIM,
    QUEST_REROLL_ALL_DONE,
    QUEST_REROLL_NOT_AVAILABLE,
    QUEST_REROLL_ONE_DONE,
    QUEST_REWARD_DUST_ONLY,
    QUEST_REWARD_DUST_TICKETS,
    QUEST_SLOT_CLAIMED_ICON,
    QUEST_SLOT_DONE_ICON,
    QUEST_SLOT_LINE,
    QUEST_SLOT_NOT_FOUND,
    QUEST_SLOT_PENDING_ICON,
    QUESTS_FOOTER,
    QUESTS_HEADER,
    REROLL_ALL_AVAILABLE,
    REROLL_ALL_USED,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="quest")

_BAR_SEGMENTS = 10


def _progress_bar(progress: int, target: int) -> str:
    filled = _BAR_SEGMENTS if target <= 0 else min(_BAR_SEGMENTS, round(_BAR_SEGMENTS * progress / target))
    return "⬛" * filled + "⬜" * (_BAR_SEGMENTS - filled)


def _reward_text(dust: int, tickets: int) -> str:
    if tickets:
        return QUEST_REWARD_DUST_TICKETS.format(dust=dust, tickets=tickets)
    return QUEST_REWARD_DUST_ONLY.format(dust=dust)


def _render_text(status: quest_service.QuestScreenStatus) -> str:
    body = "".join(
        QUEST_SLOT_LINE.format(
            icon=(
                QUEST_SLOT_CLAIMED_ICON
                if slot_view.claimed
                else QUEST_SLOT_DONE_ICON
                if slot_view.done
                else QUEST_SLOT_PENDING_ICON
            ),
            text=slot_view.text,
            bar=_progress_bar(slot_view.progress, slot_view.target),
            progress=slot_view.progress,
            target=slot_view.target,
            reward=_reward_text(slot_view.reward_dust, slot_view.reward_tickets),
        )
        for slot_view in status.slots
    )
    footer = QUESTS_FOOTER.format(
        individual_left=status.individual_rerolls_left,
        individual_limit=DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT,
        reroll_all_status=REROLL_ALL_AVAILABLE if status.reroll_all_available else REROLL_ALL_USED,
    )
    return QUESTS_HEADER + body + footer


async def _show(target: Message, session: AsyncSession, user_id: int, *, edit: bool) -> None:
    status = await quest_service.get_status(session, user_id)
    text = _render_text(status)
    markup = quests_menu(status)
    if edit:
        await safe_edit_text(target, text, reply_markup=markup)
    else:
        await target.answer(text, reply_markup=markup)


@router.message(F.text == BTN_QUESTS)
async def cmd_quests(message: Message, session: AsyncSession) -> None:
    try:
        await _show(message, session, message.from_user.id, edit=False)
    except quest_service.UserNotFoundError:
        await message.answer(NEED_START)


@router.callback_query(F.data == CB_QUEST_CLAIM_ALL)
async def cb_claim_all(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_QUEST_CLAIM)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            result = await quest_service.claim_all(session, user_id=user_id)
        except quest_service.NothingToClaimError:
            await callback.answer(QUEST_NOTHING_TO_CLAIM, show_alert=True)
            return

        await callback.answer(
            QUEST_CLAIM_ALL_DONE.format(
                count=result.count, reward=_reward_text(result.reward_dust, result.reward_tickets)
            ),
            show_alert=True,
        )
        await _show(callback.message, session, user_id, edit=True)


@router.callback_query(F.data.startswith(CB_QUEST_CLAIM_PREFIX))
async def cb_claim_one(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    slot = int(callback.data[len(CB_QUEST_CLAIM_PREFIX) :])

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_QUEST_CLAIM)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            result = await quest_service.claim(session, user_id=user_id, slot=slot)
        except quest_service.SlotNotFoundError:
            await callback.answer(QUEST_SLOT_NOT_FOUND, show_alert=True)
            return
        except quest_service.QuestAlreadyClaimedError:
            await callback.answer(QUEST_ALREADY_CLAIMED, show_alert=True)
            return
        except quest_service.QuestNotDoneError:
            await callback.answer(QUEST_NOT_DONE, show_alert=True)
            return

        await callback.answer(
            QUEST_CLAIMED_DONE.format(reward=_reward_text(result.reward_dust, result.reward_tickets)),
            show_alert=True,
        )
        await _show(callback.message, session, user_id, edit=True)


@router.callback_query(F.data == CB_QUEST_REROLL_ALL)
async def cb_reroll_all(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_QUEST_REROLL)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await quest_service.reroll_all(session, user_id=user_id)
        except quest_service.RerollNotAvailableError:
            await callback.answer(QUEST_REROLL_NOT_AVAILABLE, show_alert=True)
            return

        await callback.answer(QUEST_REROLL_ALL_DONE)
        await _show(callback.message, session, user_id, edit=True)


@router.callback_query(F.data.startswith(CB_QUEST_REROLL_PREFIX))
async def cb_reroll_one(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id
    slot = int(callback.data[len(CB_QUEST_REROLL_PREFIX) :])

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_QUEST_REROLL)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await quest_service.reroll_one(session, user_id=user_id, slot=slot)
        except quest_service.SlotNotFoundError:
            await callback.answer(QUEST_SLOT_NOT_FOUND, show_alert=True)
            return
        except quest_service.RerollNotAvailableError:
            await callback.answer(QUEST_REROLL_NOT_AVAILABLE, show_alert=True)
            return

        await callback.answer(QUEST_REROLL_ONE_DONE)
        await _show(callback.message, session, user_id, edit=True)
