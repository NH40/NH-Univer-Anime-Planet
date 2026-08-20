from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import CASINO_EMOJI, CASINO_MASS_ROLL_MAX, CASINO_ROLL_COST_COINS
from bot.constant.casino import (
    CB_CASINO_GAME_PREFIX,
    CB_CASINO_MASS_CONFIRM,
    CB_CASINO_MASS_PREFIX,
    CB_CASINO_OPEN,
    CB_CASINO_ROLL_PREFIX,
    LOCK_ACTION_CASINO_MASS_ROLL,
    LOCK_ACTION_CASINO_ROLL,
)
from bot.db.repositories.user import get_by_id
from bot.keyboards.casino import casino_menu, game_menu, mass_roll_confirm_menu
from bot.keyboards.common import back_button_menu
from bot.services import casino
from bot.states.casino import CasinoStates
from bot.texts.casino import (
    CASINO_SCREEN,
    GAME_NAMES,
    GAME_SCREEN,
    MASS_ROLL_CONFIRM,
    MASS_ROLL_INVALID,
    MASS_ROLL_PROMPT,
    MASS_ROLL_RESULT,
    ROLL_RESULT,
)
from bot.texts.common import NEED_START
from bot.texts.shop import CANCELLED, NOT_ENOUGH_COINS
from bot.utils.safe_edit import safe_edit_text

router = Router(name="casino")

_DICE_GAME = "dice"


@router.callback_query(F.data == CB_CASINO_OPEN)
async def cb_open_casino(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, CASINO_SCREEN.format(coins=user.coins), reply_markup=casino_menu())


@router.callback_query(F.data.startswith(CB_CASINO_GAME_PREFIX))
async def cb_open_game(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    game = callback.data[len(CB_CASINO_GAME_PREFIX) :]
    if game not in CASINO_EMOJI:
        await callback.answer()
        return

    # Точка возврата "Назад" для waiting_mass_roll_quantity (см. CLAUDE.md, 2026-08-21).
    await state.clear()
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return

    text = GAME_SCREEN.format(
        emoji=CASINO_EMOJI[game], name=GAME_NAMES[game], price=CASINO_ROLL_COST_COINS, coins=user.coins
    )
    await safe_edit_text(callback.message, text, reply_markup=game_menu(game, allow_mass_roll=game == _DICE_GAME))


@router.callback_query(F.data.startswith(CB_CASINO_ROLL_PREFIX))
async def cb_roll(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    game = callback.data[len(CB_CASINO_ROLL_PREFIX) :]
    if game not in CASINO_EMOJI:
        await callback.answer()
        return

    user_id = callback.from_user.id
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CASINO_ROLL)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await casino.charge_roll(session, user_id=user_id)
        except casino.NotEnoughCoinsError as exc:
            await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer()
        dice_message = await callback.message.answer_dice(emoji=CASINO_EMOJI[game])
        value = dice_message.dice.value

        await casino.grant_roll_reward(session, user_id=user_id, roll_value=value)

        await callback.message.answer(ROLL_RESULT.format(emoji=CASINO_EMOJI[game], value=value))


@router.callback_query(F.data.startswith(CB_CASINO_MASS_PREFIX))
async def cb_mass_roll_start(callback: CallbackQuery, state: FSMContext) -> None:
    game = callback.data[len(CB_CASINO_MASS_PREFIX) :]
    if game != _DICE_GAME:
        # Масс-крутка — только кубик (решение пользователя), остальные игры сюда не должны
        # попадать (кнопка для них не строится), но на всякий случай не ломаемся молча.
        await callback.answer()
        return

    await state.set_state(CasinoStates.waiting_mass_roll_quantity)
    await state.update_data(game=game)
    await callback.answer()
    await callback.message.answer(
        MASS_ROLL_PROMPT.format(max=CASINO_MASS_ROLL_MAX), reply_markup=back_button_menu(f"{CB_CASINO_GAME_PREFIX}{game}")
    )


@router.message(StateFilter(CasinoStates.waiting_mass_roll_quantity), Command("cancel"))
async def cancel_mass_roll(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(CANCELLED)


@router.message(StateFilter(CasinoStates.waiting_mass_roll_quantity))
async def apply_mass_roll_quantity(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (1 <= int(raw) <= CASINO_MASS_ROLL_MAX):
        await message.answer(MASS_ROLL_INVALID.format(max=CASINO_MASS_ROLL_MAX))
        return

    quantity = int(raw)
    cost = quantity * CASINO_ROLL_COST_COINS
    await state.update_data(quantity=quantity)
    await message.answer(MASS_ROLL_CONFIRM.format(qty=quantity, cost=cost), reply_markup=mass_roll_confirm_menu())


@router.callback_query(StateFilter(CasinoStates.waiting_mass_roll_quantity), F.data == CB_CASINO_MASS_CONFIRM)
async def cb_confirm_mass_roll(callback: CallbackQuery, state: FSMContext, session: AsyncSession, redis: Redis) -> None:
    data = await state.get_data()
    quantity = data.get("quantity")
    game = data.get("game", _DICE_GAME)
    await state.clear()

    if quantity is None:
        await callback.answer(CANCELLED, show_alert=True)
        return

    user_id = callback.from_user.id
    # До CASINO_MASS_ROLL_MAX последовательных вызовов answer_dice — дефолтных 3с лока может
    # не хватить (см. аналогичный случай с крутка x10 в deck.py), берём лок с запасом.
    async with try_acquire(redis, action_lock(user_id, LOCK_ACTION_CASINO_MASS_ROLL), ttl_ms=20000) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            cost = await casino.charge_mass_roll(session, user_id=user_id, quantity=quantity)
        except casino.NotEnoughCoinsError as exc:
            await callback.answer(NOT_ENOUGH_COINS.format(needed=exc.needed), show_alert=True)
            return

        await callback.answer()

        values: list[int] = []
        for _ in range(quantity):
            dice_message = await callback.message.answer_dice(emoji=CASINO_EMOJI[game])
            values.append(dice_message.dice.value)

        total = sum(values)
        await casino.grant_mass_roll_reward(session, user_id=user_id, total_value=total)

        await callback.message.answer(
            MASS_ROLL_RESULT.format(values=", ".join(map(str, values)), total=total, cost=cost)
        )
