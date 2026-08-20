from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import EVENT_CARD_UBP
from bot.constant.dust import (
    CB_DUST_ALL_ASK_PREFIX,
    CB_DUST_ALL_PREFIX,
    CB_DUST_AMOUNT_ASK_PREFIX,
    CB_DUST_AMOUNT_PREFIX,
    CB_DUST_CUSTOM_PREFIX,
    CB_DUST_DUPES_ASK_PREFIX,
    CB_DUST_DUPES_PREFIX,
    CB_DUST_EVENTS,
    CB_DUST_MODE_ALL,
    CB_DUST_MODE_ALL_CONFIRM,
    CB_DUST_MODE_CANCEL,
    CB_DUST_MODE_DUPES,
    CB_DUST_MODE_DUPES_CONFIRM,
    CB_DUST_OPEN,
    CB_DUST_SELECT,
    CB_DUST_STACK_PREFIX,
    CB_DUST_TIER_PAGE_PREFIX,
    CB_DUST_TIER_PREFIX,
    LOCK_ACTION_DUST,
)
from bot.db.repositories.inventory import OwnedStack, list_owned_stacks_in_event_universes, list_owned_stacks_in_tier
from bot.db.repositories.universe import get_by_code as get_universe
from bot.db.repositories.user import get_by_id
from bot.keyboards.common import back_button_menu
from bot.keyboards.dust import card_actions, confirm_menu, mode_menu, point_confirm_menu, stack_list, tier_picker
from bot.services import dust
from bot.states.dust import DustStates
from bot.texts.common import NEED_START
from bot.texts.deck import NO_UNIVERSE_SELECTED
from bot.texts.dust import (
    BULK_NOTHING,
    BULK_RESULT,
    CARD_ACTION_HEADER,
    CONFIRM_ALL,
    CONFIRM_ALL_ONE,
    CONFIRM_AMOUNT,
    CONFIRM_DUPES,
    CONFIRM_DUPES_ONE,
    CUSTOM_AMOUNT_CANCELLED,
    CUSTOM_AMOUNT_INVALID,
    CUSTOM_AMOUNT_PROMPT,
    DUST_NOT_ENOUGH,
    DUST_NOTHING,
    DUST_OPEN_HEADER,
    DUST_RESULT,
    DUST_STACK_LIST_HEADER,
    DUST_TIER_PICKER_HEADER,
    EMPTY_TIER,
)
from bot.utils.formatting import esc
from bot.utils.safe_edit import safe_edit_text

router = Router(name="dust")


async def _stacks(session: AsyncSession, user_id: int, universe_code: str | None, tier: int) -> list[OwnedStack]:
    if tier == EVENT_CARD_UBP:
        return await list_owned_stacks_in_event_universes(session, user_id)
    return await list_owned_stacks_in_tier(session, user_id=user_id, universe_code=universe_code, base_ubp=tier)


def _parse_tier_page(data: str, prefix: str) -> tuple[int, int]:
    tier_s, page_s = data[len(prefix) :].split(":")
    return int(tier_s), int(page_s)


def _parse_stack_key(data: str, prefix: str) -> tuple[int, int, int]:
    tier_s, card_s, stars_s = data[len(prefix) :].split(":")
    return int(tier_s), int(card_s), int(stars_s)


def _parse_amount_key(data: str, prefix: str) -> tuple[int, int, int, int]:
    tier_s, card_s, stars_s, amount_s = data[len(prefix) :].split(":")
    return int(tier_s), int(card_s), int(stars_s), int(amount_s)


async def _render_tier(callback: CallbackQuery, session: AsyncSession, *, universe_code: str | None, tier: int, page: int) -> None:
    stacks = await _stacks(session, callback.from_user.id, universe_code, tier)
    if not stacks:
        await safe_edit_text(callback.message, EMPTY_TIER, reply_markup=tier_picker())
        return
    await safe_edit_text(
        callback.message, DUST_STACK_LIST_HEADER, reply_markup=stack_list(tier=tier, stacks=stacks, page=page)
    )


@router.callback_query(F.data == CB_DUST_OPEN)
async def cb_open_dust(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return
    await callback.answer()
    await safe_edit_text(callback.message, DUST_OPEN_HEADER, reply_markup=mode_menu())


@router.callback_query(F.data == CB_DUST_MODE_ALL)
async def cb_mode_all(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, CONFIRM_ALL, reply_markup=confirm_menu(CB_DUST_MODE_ALL_CONFIRM))


@router.callback_query(F.data == CB_DUST_MODE_DUPES)
async def cb_mode_dupes(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, CONFIRM_DUPES, reply_markup=confirm_menu(CB_DUST_MODE_DUPES_CONFIRM))


@router.callback_query(F.data == CB_DUST_MODE_CANCEL)
async def cb_mode_cancel(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, DUST_OPEN_HEADER, reply_markup=mode_menu())


async def _bulk_distill(callback: CallbackQuery, session: AsyncSession, redis: Redis, *, keep_one: bool) -> None:
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_DUST)) as acquired:
        if not acquired:
            await callback.answer()
            return

        reward = await dust.distill_all_owned(session, user_id=user_id, keep_one=keep_one)
        if not reward:
            await callback.answer(BULK_NOTHING, show_alert=True)
        else:
            await callback.answer(BULK_RESULT.format(reward=reward), show_alert=True)
        await safe_edit_text(callback.message, DUST_OPEN_HEADER, reply_markup=mode_menu())


@router.callback_query(F.data == CB_DUST_MODE_ALL_CONFIRM)
async def cb_mode_all_confirm(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _bulk_distill(callback, session, redis, keep_one=False)


@router.callback_query(F.data == CB_DUST_MODE_DUPES_CONFIRM)
async def cb_mode_dupes_confirm(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    await _bulk_distill(callback, session, redis, keep_one=True)


@router.callback_query(F.data == CB_DUST_SELECT)
async def cb_select_mode(callback: CallbackQuery, session: AsyncSession) -> None:
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
        callback.message, DUST_TIER_PICKER_HEADER.format(universe=esc(universe.title)), reply_markup=tier_picker()
    )


@router.callback_query(F.data == CB_DUST_EVENTS)
async def cb_open_events(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer()
        await callback.message.answer(NEED_START)
        return
    await callback.answer()
    await _render_tier(callback, session, universe_code=None, tier=EVENT_CARD_UBP, page=1)


@router.callback_query(F.data.startswith(CB_DUST_TIER_PREFIX))
async def cb_open_tier(callback: CallbackQuery, session: AsyncSession) -> None:
    tier = int(callback.data[len(CB_DUST_TIER_PREFIX) :])
    user = await get_by_id(session, callback.from_user.id)
    if user is None or user.universe_selected is None:
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return
    await callback.answer()
    await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)


@router.callback_query(F.data.startswith(CB_DUST_TIER_PAGE_PREFIX))
async def cb_tier_page(callback: CallbackQuery, session: AsyncSession) -> None:
    tier, page = _parse_tier_page(callback.data, CB_DUST_TIER_PAGE_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return
    await callback.answer()
    await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=page)


async def _find_stack(session: AsyncSession, user_id: int, universe_code: str | None, tier: int, card_id: int, stars: int) -> OwnedStack | None:
    stacks = await _stacks(session, user_id, universe_code, tier)
    return next((s for s in stacks if s.card.id == card_id and s.stars == stars), None)


@router.callback_query(F.data.startswith(CB_DUST_STACK_PREFIX))
async def cb_select_stack(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, CB_DUST_STACK_PREFIX)
    # Точка возврата "Назад" для флоу ввода своего числа (см. CLAUDE.md, 2026-08-21).
    await state.clear()
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    match = await _find_stack(session, callback.from_user.id, user.universe_selected, tier, card_id, stars)
    await callback.answer()
    if match is None:
        await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)
        return

    await safe_edit_text(
        callback.message,
        CARD_ACTION_HEADER.format(name=esc(match.card.name), stars="🌟" * stars, quantity=match.quantity),
        reply_markup=card_actions(tier=tier, card_id=card_id, stars=stars),
    )


async def _refresh_after_point_action(callback: CallbackQuery, session: AsyncSession, *, tier: int, universe_code: str | None) -> None:
    await _render_tier(callback, session, universe_code=universe_code, tier=tier, page=1)


@router.callback_query(F.data.startswith(CB_DUST_AMOUNT_ASK_PREFIX))
async def cb_dust_amount_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    tier, card_id, stars, amount = _parse_amount_key(callback.data, CB_DUST_AMOUNT_ASK_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    match = await _find_stack(session, callback.from_user.id, user.universe_selected, tier, card_id, stars)
    await callback.answer()
    if match is None:
        await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)
        return

    key = f"{tier}:{card_id}:{stars}:{amount}"
    await safe_edit_text(
        callback.message,
        CONFIRM_AMOUNT.format(amount=amount, name=esc(match.card.name), stars="🌟" * stars),
        reply_markup=point_confirm_menu(
            confirm_callback=f"{CB_DUST_AMOUNT_PREFIX}{key}",
            cancel_callback=f"{CB_DUST_STACK_PREFIX}{tier}:{card_id}:{stars}",
        ),
    )


@router.callback_query(F.data.startswith(CB_DUST_AMOUNT_PREFIX))
async def cb_dust_amount(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, card_id, stars, amount = _parse_amount_key(callback.data, CB_DUST_AMOUNT_PREFIX)
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_DUST)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        try:
            reward = await dust.distill_amount(session, user_id=user_id, card_id=card_id, stars=stars, amount=amount)
        except dust.NotEnoughCopiesError as exc:
            await callback.answer(DUST_NOT_ENOUGH.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer(DUST_RESULT.format(count=amount, reward=reward), show_alert=True)
        await _refresh_after_point_action(callback, session, tier=tier, universe_code=user.universe_selected)


@router.callback_query(F.data.startswith(CB_DUST_DUPES_ASK_PREFIX))
async def cb_dust_dupes_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    await _dust_keep_ask(
        callback, session, prefix=CB_DUST_DUPES_ASK_PREFIX, confirm_prefix=CB_DUST_DUPES_PREFIX, text=CONFIRM_DUPES_ONE
    )


@router.callback_query(F.data.startswith(CB_DUST_ALL_ASK_PREFIX))
async def cb_dust_all_ask(callback: CallbackQuery, session: AsyncSession) -> None:
    await _dust_keep_ask(
        callback, session, prefix=CB_DUST_ALL_ASK_PREFIX, confirm_prefix=CB_DUST_ALL_PREFIX, text=CONFIRM_ALL_ONE
    )


async def _dust_keep_ask(callback: CallbackQuery, session: AsyncSession, *, prefix: str, confirm_prefix: str, text: str) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, prefix)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    match = await _find_stack(session, callback.from_user.id, user.universe_selected, tier, card_id, stars)
    await callback.answer()
    if match is None:
        await _render_tier(callback, session, universe_code=user.universe_selected, tier=tier, page=1)
        return

    key = f"{tier}:{card_id}:{stars}"
    await safe_edit_text(
        callback.message,
        text.format(name=esc(match.card.name), stars="🌟" * stars, quantity=match.quantity),
        reply_markup=point_confirm_menu(
            confirm_callback=f"{confirm_prefix}{key}", cancel_callback=f"{CB_DUST_STACK_PREFIX}{key}"
        ),
    )


@router.callback_query(F.data.startswith(CB_DUST_DUPES_PREFIX))
async def cb_dust_dupes(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, CB_DUST_DUPES_PREFIX)
    await _dust_keep(callback, session, redis, tier=tier, card_id=card_id, stars=stars, keep_one=True)


@router.callback_query(F.data.startswith(CB_DUST_ALL_PREFIX))
async def cb_dust_all(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, CB_DUST_ALL_PREFIX)
    await _dust_keep(callback, session, redis, tier=tier, card_id=card_id, stars=stars, keep_one=False)


async def _dust_keep(
    callback: CallbackQuery, session: AsyncSession, redis: Redis, *, tier: int, card_id: int, stars: int, keep_one: bool
) -> None:
    user_id = callback.from_user.id

    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_DUST)) as acquired:
        if not acquired:
            await callback.answer()
            return

        user = await get_by_id(session, user_id)
        if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
            await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
            return

        try:
            reward = await dust.distill(session, user_id=user_id, card_id=card_id, stars=stars, keep_one=keep_one)
        except dust.NothingToDistillError:
            await callback.answer(DUST_NOTHING, show_alert=True)
            return

        await callback.answer(BULK_RESULT.format(reward=reward), show_alert=True)
        await _refresh_after_point_action(callback, session, tier=tier, universe_code=user.universe_selected)


@router.callback_query(F.data.startswith(CB_DUST_CUSTOM_PREFIX))
async def cb_custom_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    tier, card_id, stars = _parse_stack_key(callback.data, CB_DUST_CUSTOM_PREFIX)
    user = await get_by_id(session, callback.from_user.id)
    if user is None or (tier != EVENT_CARD_UBP and user.universe_selected is None):
        await callback.answer(NO_UNIVERSE_SELECTED, show_alert=True)
        return

    match = await _find_stack(session, callback.from_user.id, user.universe_selected, tier, card_id, stars)
    if match is None:
        await callback.answer(DUST_NOTHING, show_alert=True)
        return

    await state.update_data(tier=tier, card_id=card_id, stars=stars)
    await state.set_state(DustStates.waiting_amount)
    await callback.answer()
    await callback.message.answer(
        CUSTOM_AMOUNT_PROMPT.format(max=match.quantity),
        reply_markup=back_button_menu(f"{CB_DUST_STACK_PREFIX}{tier}:{card_id}:{stars}"),
    )


@router.message(StateFilter(DustStates.waiting_amount), Command("cancel"))
async def cancel_custom_amount(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CUSTOM_AMOUNT_CANCELLED)


@router.message(StateFilter(DustStates.waiting_amount))
async def apply_custom_amount(message: Message, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    tier, card_id, stars = data["tier"], data["card_id"], data["stars"]
    user_id = message.from_user.id

    user = await get_by_id(session, user_id)
    universe_code = user.universe_selected if user is not None else None
    # Актуальное количество на момент применения (могло измениться с момента промпта) —
    # тот же принцип, что и в остальных FSM-флоу проекта (см. CLAUDE.md).
    match = await _find_stack(session, user_id, universe_code, tier, card_id, stars)
    if match is None:
        await state.clear()
        await message.answer(DUST_NOTHING)
        return

    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= match.quantity):
        await message.answer(CUSTOM_AMOUNT_INVALID.format(max=match.quantity))
        return

    amount = int(raw)
    await state.clear()

    # Число ввели текстом — само по себе уже осмысленное действие, но всё равно не
    # исполняем сразу: тот же экран подтверждения, что у пресетов 1/5/10 (см. cb_dust_amount_ask,
    # подтверждено пользователем 2026-08-14).
    key = f"{tier}:{card_id}:{stars}:{amount}"
    await message.answer(
        CONFIRM_AMOUNT.format(amount=amount, name=esc(match.card.name), stars="🌟" * stars),
        reply_markup=point_confirm_menu(
            confirm_callback=f"{CB_DUST_AMOUNT_PREFIX}{key}",
            cancel_callback=f"{CB_DUST_STACK_PREFIX}{tier}:{card_id}:{stars}",
        ),
    )
