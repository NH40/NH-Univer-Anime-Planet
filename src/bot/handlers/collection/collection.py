from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InputMediaPhoto
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import MERGE_COPIES_REQUIRED, ubp_for_stars
from bot.constant.collection import (
    CB_COLL_DUST1_PREFIX,
    CB_COLL_DUSTALL_PREFIX,
    CB_COLL_MERGE_PREFIX,
    CB_COLL_NAV_PREFIX,
    CB_COLL_TIER_PREFIX,
    LOCK_ACTION_DUST,
    LOCK_ACTION_MERGE,
)
from bot.constant.deck import CB_DECK_COLLECTION
from bot.db.repositories.inventory import OwnedStack, list_owned_stacks_in_tier
from bot.db.repositories.universe import get_by_code as get_universe
from bot.db.repositories.user import get_by_id
from bot.keyboards.collection import stack_view, tier_picker
from bot.services import dust, merge
from bot.texts.collection import (
    DUST_NOTHING,
    DUST_RESULT,
    EMPTY_TIER,
    MERGE_NOT_ENOUGH,
    MERGE_RESULT,
    NO_ACTIVE_SEASON,
    STACK_CAPTION,
    TIER_PICKER_HEADER,
)
from bot.texts.common import NEED_START
from bot.texts.deck import NO_UNIVERSE_SELECTED
from bot.utils.card_media import card_photo
from bot.utils.formatting import esc
from bot.utils.safe_edit import safe_edit_media, safe_edit_text

router = Router(name="collection")


async def _stacks(session: AsyncSession, user_id: int, universe_code: str, tier: int) -> list[OwnedStack]:
    return await list_owned_stacks_in_tier(session, user_id=user_id, universe_code=universe_code, base_ubp=tier)


def _stack_caption(stack: OwnedStack, index: int, total: int) -> str:
    return STACK_CAPTION.format(
        external_id=esc(stack.card.external_id),
        name=esc(stack.card.name),
        stars="🌟" * stack.stars,
        ubp=ubp_for_stars(stack.card.base_ubp, stack.stars),
        quantity=stack.quantity,
        position=index + 1,
        total=total,
    )


def _parse_tier_index(data: str, prefix: str) -> tuple[int, int]:
    tier_s, index_s = data[len(prefix) :].split(":")
    return int(tier_s), int(index_s)


@router.callback_query(F.data == CB_DECK_COLLECTION)
async def cb_open_collection(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return
    if user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    universe = await get_universe(session, user.universe_selected)
    await callback.answer()
    # Открываем из текстового экрана "Колода" — тоже текст, можно редактировать на месте.
    await safe_edit_text(
        callback.message, TIER_PICKER_HEADER.format(universe=esc(universe.title)), reply_markup=tier_picker()
    )


@router.callback_query(F.data.startswith(CB_COLL_TIER_PREFIX))
async def cb_open_tier(callback: CallbackQuery, session: AsyncSession) -> None:
    tier = int(callback.data[len(CB_COLL_TIER_PREFIX) :])
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    stacks = await _stacks(session, callback.from_user.id, user.universe_selected, tier)
    await callback.answer()
    if not stacks:
        # Источник — тир-пикер, тоже текст, поэтому редактируем на месте, а не спамим.
        await safe_edit_text(callback.message, EMPTY_TIER, reply_markup=tier_picker())
        return

    # Тир-пикер — текст, карточка — фото, редактировать на месте нельзя (разные типы
    # контента у Telegram), поэтому новое сообщение.
    await callback.message.answer_photo(
        card_photo(stacks[0].card),
        caption=_stack_caption(stacks[0], 0, len(stacks)),
        reply_markup=stack_view(tier=tier, index=0, total=len(stacks), quantity=stacks[0].quantity),
    )


@router.callback_query(F.data.startswith(CB_COLL_NAV_PREFIX))
async def cb_navigate(callback: CallbackQuery, session: AsyncSession) -> None:
    tier, index = _parse_tier_index(callback.data, CB_COLL_NAV_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    stacks = await _stacks(session, callback.from_user.id, user.universe_selected, tier)
    await callback.answer()
    if not stacks:
        await callback.message.answer(EMPTY_TIER, reply_markup=tier_picker())
        return

    index = max(0, min(index, len(stacks) - 1))
    stack = stacks[index]
    await safe_edit_media(
        callback.message,
        InputMediaPhoto(media=card_photo(stack.card), caption=_stack_caption(stack, index, len(stacks))),
        reply_markup=stack_view(tier=tier, index=index, total=len(stacks), quantity=stack.quantity),
    )


async def _refresh_after_action(callback: CallbackQuery, session: AsyncSession, universe_code: str, tier: int) -> None:
    """После распыления/слияния состав стопок в тире мог измениться — просто
    показываем тир заново с начала, а не пытаемся угадать, куда делась старая позиция."""
    stacks = await _stacks(session, callback.from_user.id, universe_code, tier)
    if not stacks:
        await callback.message.answer(EMPTY_TIER, reply_markup=tier_picker())
        return
    await safe_edit_media(
        callback.message,
        InputMediaPhoto(media=card_photo(stacks[0].card), caption=_stack_caption(stacks[0], 0, len(stacks))),
        reply_markup=stack_view(tier=tier, index=0, total=len(stacks), quantity=stacks[0].quantity),
    )


@router.callback_query(F.data.startswith(CB_COLL_DUST1_PREFIX) | F.data.startswith(CB_COLL_DUSTALL_PREFIX))
async def cb_dust(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    keep_one = callback.data.startswith(CB_COLL_DUST1_PREFIX)
    prefix = CB_COLL_DUST1_PREFIX if keep_one else CB_COLL_DUSTALL_PREFIX
    tier, index = _parse_tier_index(callback.data, prefix)
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_DUST)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or user.universe_selected is None:
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        stacks = await _stacks(session, user_id, user.universe_selected, tier)
        if index >= len(stacks):
            await callback.answer(DUST_NOTHING, show_alert=True)
            return
        stack = stacks[index]

        try:
            reward = await dust.distill(
                session, user_id=user_id, card_id=stack.card.id, stars=stack.stars, keep_one=keep_one
            )
        except dust.NothingToDistillError:
            await callback.answer(DUST_NOTHING, show_alert=True)
            return

        dusted_count = stack.quantity - (1 if keep_one else 0)
        await callback.answer(DUST_RESULT.format(count=dusted_count, reward=reward), show_alert=True)
        await _refresh_after_action(callback, session, user.universe_selected, tier)


@router.callback_query(F.data.startswith(CB_COLL_MERGE_PREFIX))
async def cb_merge(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, index = _parse_tier_index(callback.data, CB_COLL_MERGE_PREFIX)
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_MERGE)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or user.universe_selected is None:
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        stacks = await _stacks(session, user_id, user.universe_selected, tier)
        if index >= len(stacks):
            await callback.answer(MERGE_NOT_ENOUGH.format(needed=MERGE_COPIES_REQUIRED), show_alert=True)
            return
        stack = stacks[index]

        try:
            result = await merge.merge_stack(
                session, redis, user_id=user_id, card_id=stack.card.id, stars=stack.stars
            )
        except merge.NotEnoughCopiesError as exc:
            await callback.answer(MERGE_NOT_ENOUGH.format(needed=exc.needed), show_alert=True)
            return
        except merge.NoActiveSeasonError:
            await callback.answer(NO_ACTIVE_SEASON, show_alert=True)
            return

        await callback.answer(
            MERGE_RESULT.format(
                name=result.card.name, stars="🌟" * result.new_stars, ubp=result.new_ubp, bonus=result.bonus_ubp
            ),
            show_alert=True,
        )
        await _refresh_after_action(callback, session, user.universe_selected, tier)
