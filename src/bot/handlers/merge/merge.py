from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import EVENT_CARD_UBP, MAX_STARS, MERGE_COPIES_REQUIRED
from bot.constant.merge import (
    CB_MERGE_ACTION_PREFIX,
    CB_MERGE_ALL_TO_MAX,
    CB_MERGE_EVENTS,
    CB_MERGE_OPEN,
    CB_MERGE_STACK_PREFIX,
    CB_MERGE_TIER_PAGE_PREFIX,
    CB_MERGE_TIER_PREFIX,
    LOCK_ACTION_MERGE,
)
from bot.db.repositories.inventory import OwnedStack, list_owned_stacks_in_event_universes, list_owned_stacks_in_tier
from bot.db.repositories.universe import get_by_code as get_universe
from bot.db.repositories.user import get_by_id
from bot.keyboards.merge import card_actions, merge_tier_picker, stack_list
from bot.services import merge
from bot.texts.common import NEED_START
from bot.texts.deck import NO_UNIVERSE_SELECTED
from bot.texts.merge import (
    CARD_ACTION_HEADER,
    EMPTY_TIER,
    MERGE_ALL_TO_MAX_NOTHING,
    MERGE_ALL_TO_MAX_RESULT,
    MERGE_NOT_ENOUGH,
    MERGE_RESULT,
    MERGE_STACK_LIST_HEADER,
    MERGE_TIER_PICKER_HEADER,
    NO_ACTIVE_SEASON,
)
from bot.utils.formatting import esc
from bot.utils.safe_edit import safe_edit_text

router = Router(name="merge")


async def _stacks(session: AsyncSession, user_id: int, universe_code: str | None, tier: int) -> list[OwnedStack]:
    if tier == EVENT_CARD_UBP:
        return await list_owned_stacks_in_event_universes(session, user_id)
    return await list_owned_stacks_in_tier(session, user_id=user_id, universe_code=universe_code, base_ubp=tier)


def _eligible(stacks: list[OwnedStack]) -> list[OwnedStack]:
    return [s for s in stacks if s.stars < MAX_STARS and s.quantity >= MERGE_COPIES_REQUIRED]


def _parse_tier_page(data: str, prefix: str) -> tuple[int, int]:
    tier_s, page_s = data[len(prefix) :].split(":")
    return int(tier_s), int(page_s)


def _parse_stack_key(data: str, prefix: str) -> tuple[int, int, int]:
    tier_s, card_s, stars_s = data[len(prefix) :].split(":")
    return int(tier_s), int(card_s), int(stars_s)


def _parse_action_key(data: str, prefix: str) -> tuple[int, int, int, int, bool]:
    tier_s, card_s, stars_s, target_s, mode_s = data[len(prefix) :].split(":")
    return int(tier_s), int(card_s), int(stars_s), int(target_s), mode_s == "1"


async def _render_tier(callback: CallbackQuery, session: AsyncSession, *, universe_code: str | None, tier: int, page: int) -> None:
    stacks = _eligible(await _stacks(session, callback.from_user.id, universe_code, tier))
    if not stacks:
        await safe_edit_text(callback.message, EMPTY_TIER, reply_markup=merge_tier_picker())
        return
    await safe_edit_text(
        callback.message, MERGE_STACK_LIST_HEADER, reply_markup=stack_list(tier=tier, stacks=stacks, page=page)
    )


@router.callback_query(F.data == CB_MERGE_OPEN)
async def cb_open_merge(callback: CallbackQuery, session: AsyncSession) -> None:
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
    await safe_edit_text(
        callback.message, MERGE_TIER_PICKER_HEADER.format(universe=esc(universe.title)), reply_markup=merge_tier_picker()
    )


@router.callback_query(F.data == CB_MERGE_EVENTS)
async def cb_open_events(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return

    await callback.answer()
    await _render_tier(callback, session, universe_code=None, tier=EVENT_CARD_UBP, page=1)


@router.callback_query(F.data.startswith(CB_MERGE_TIER_PREFIX))
async def cb_open_tier(callback: CallbackQuery, session: AsyncSession) -> None:
    tier = int(callback.data[len(CB_MERGE_TIER_PREFIX) :])
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    await callback.answer()
    await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)


@router.callback_query(F.data.startswith(CB_MERGE_TIER_PAGE_PREFIX))
async def cb_tier_page(callback: CallbackQuery, session: AsyncSession) -> None:
    tier, page = _parse_tier_page(callback.data, CB_MERGE_TIER_PAGE_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    await callback.answer()
    await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=page)


@router.callback_query(F.data.startswith(CB_MERGE_STACK_PREFIX))
async def cb_select_stack(callback: CallbackQuery, session: AsyncSession) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, CB_MERGE_STACK_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    stacks = await _stacks(session, callback.from_user.id, user.universe_selected, tier)
    match = next((s for s in stacks if s.card.id == card_id and s.stars == stars), None)
    await callback.answer()
    if match is None:
        # Стопка исчезла между экранами (уже смёржена/распылена откуда-то ещё) — просто
        # показать список заново, а не падать на пустых данных.
        await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)
        return

    await safe_edit_text(
        callback.message,
        CARD_ACTION_HEADER.format(name=esc(match.card.name), stars="🌟" * stars, quantity=match.quantity),
        reply_markup=card_actions(tier=tier, card_id=card_id, stars=stars),
    )


@router.callback_query(F.data.startswith(CB_MERGE_ACTION_PREFIX))
async def cb_merge_action(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, card_id, stars, target, single = _parse_action_key(callback.data, CB_MERGE_ACTION_PREFIX)
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_MERGE)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        try:
            summary = await merge.merge_to_target(
                session, redis, user_id=user_id, card_id=card_id, stars=stars, target_stars=target, single=single
            )
        except merge.NotEnoughCopiesError as exc:
            await callback.answer(MERGE_NOT_ENOUGH.format(needed=exc.needed), show_alert=True)
            return
        except merge.NoActiveSeasonError:
            await callback.answer(NO_ACTIVE_SEASON, show_alert=True)
            return

        await callback.answer(
            MERGE_RESULT.format(
                events=summary.events, name=summary.card.name, stars="🌟" * summary.final_stars, bonus=summary.total_bonus
            ),
            show_alert=True,
        )
        await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)


@router.callback_query(F.data == CB_MERGE_ALL_TO_MAX)
async def cb_merge_all_to_max(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_MERGE)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or user.universe_selected is None:
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        try:
            summaries = await merge.merge_all_to_max_in_universe(
                session, redis, user_id=user_id, universe_code=user.universe_selected
            )
        except merge.NoActiveSeasonError:
            await callback.answer(NO_ACTIVE_SEASON, show_alert=True)
            return

        if not summaries:
            await callback.answer(MERGE_ALL_TO_MAX_NOTHING.format(max=MAX_STARS), show_alert=True)
            return

        total_events = sum(s.events for s in summaries)
        total_bonus = sum(s.total_bonus for s in summaries)
        await callback.answer(
            MERGE_ALL_TO_MAX_RESULT.format(cards=len(summaries), events=total_events, bonus=total_bonus), show_alert=True
        )

        universe = await get_universe(session, user.universe_selected)
        await safe_edit_text(
            callback.message, MERGE_TIER_PICKER_HEADER.format(universe=esc(universe.title)), reply_markup=merge_tier_picker()
        )
