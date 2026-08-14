from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.clan import CB_CLAN_EXCHANGE_CURRENCY_PREFIX, CB_CLAN_EXCHANGE_MEMBER_PREFIX, CB_CLAN_EXCHANGE_START, LOCK_ACTION_EXCHANGE
from bot.db.models.enums import TransactionCurrency
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.handlers.clan.clan import render_clan_card
from bot.keyboards.clan import exchange_amount_menu, exchange_currency_menu, exchange_member_menu
from bot.services import clan as clan_service
from bot.states.clan import ClanStates
from bot.texts.clan import (
    ACTION_CANCELLED,
    CURRENCY_NAMES_GENITIVE,
    EXCHANGE_CHOOSE_CURRENCY,
    EXCHANGE_CHOOSE_MEMBER,
    EXCHANGE_DONE,
    EXCHANGE_INVALID,
    EXCHANGE_NO_MEMBERS,
    EXCHANGE_NOT_ENOUGH,
    EXCHANGE_NOT_IN_CLAN,
    EXCHANGE_PROMPT,
    EXCHANGE_TARGET_GONE,
    NOTIFY_EXCHANGE_RECEIVED,
    NOT_IN_CLAN,
)
from bot.utils.formatting import esc, format_number
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_exchange")

# Флоу (переработан 2026-08-14, подтверждено пользователем): Обмен -> выбрать игрока
# (список участников клана, не ввод @username) -> выбрать ресурс -> ввести количество ->
# результат возвращает в меню клана. Кнопка "Назад" на каждом промежуточном шаге.


@router.callback_query(F.data == CB_CLAN_EXCHANGE_START)
async def cb_exchange_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return

    await state.clear()
    rows = await clan_service.list_members_with_users(session, member.clan_id)
    members = [(u.id, esc(u.display_name)) for m, u in rows if u.id != callback.from_user.id]

    await callback.answer()
    if not members:
        await safe_edit_text(callback.message, EXCHANGE_NO_MEMBERS, reply_markup=exchange_member_menu([]))
        return
    await safe_edit_text(callback.message, EXCHANGE_CHOOSE_MEMBER, reply_markup=exchange_member_menu(members))


@router.callback_query(F.data.startswith(CB_CLAN_EXCHANGE_MEMBER_PREFIX))
async def cb_exchange_member(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    target_user_id = int(callback.data[len(CB_CLAN_EXCHANGE_MEMBER_PREFIX) :])
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return

    target_member = await clan_repo.get_member(session, target_user_id)
    if target_member is None or target_member.clan_id != member.clan_id:
        await callback.answer(EXCHANGE_TARGET_GONE, show_alert=True)
        await cb_exchange_start(callback, session, state)
        return

    target = await get_user_by_id(session, target_user_id)
    await state.clear()
    await callback.answer()
    await safe_edit_text(
        callback.message,
        EXCHANGE_CHOOSE_CURRENCY.format(name=esc(target.display_name) if target else str(target_user_id)),
        reply_markup=exchange_currency_menu(target_user_id),
    )


@router.callback_query(F.data.startswith(CB_CLAN_EXCHANGE_CURRENCY_PREFIX))
async def cb_exchange_currency(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return

    target_str, _, currency_value = callback.data[len(CB_CLAN_EXCHANGE_CURRENCY_PREFIX) :].partition(":")
    if not target_str.isdigit() or currency_value not in CURRENCY_NAMES_GENITIVE:
        await callback.answer()
        return
    target_user_id = int(target_str)

    target_member = await clan_repo.get_member(session, target_user_id)
    if target_member is None or target_member.clan_id != member.clan_id:
        await callback.answer(EXCHANGE_TARGET_GONE, show_alert=True)
        await cb_exchange_start(callback, session, state)
        return
    target = await get_user_by_id(session, target_user_id)

    await state.set_state(ClanStates.waiting_exchange_input)
    await state.update_data(target_user_id=target_user_id, currency=currency_value)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        EXCHANGE_PROMPT.format(
            currency=CURRENCY_NAMES_GENITIVE[currency_value],
            name=esc(target.display_name) if target else str(target_user_id),
        ),
        reply_markup=exchange_amount_menu(target_user_id),
    )


@router.message(StateFilter(ClanStates.waiting_exchange_input), Command("cancel"))
async def cancel_exchange(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_exchange_input))
async def apply_exchange(message: Message, state: FSMContext, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(EXCHANGE_INVALID)
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    currency_value = data.get("currency")
    await state.clear()
    if target_user_id is None or currency_value not in CURRENCY_NAMES_GENITIVE:
        # FSM-данные потерялись (например, истёк Redis-стораж) — не должно случаться в
        # норме, но лучше явно попросить начать заново, чем упасть на TransactionCurrency(...).
        await message.answer(EXCHANGE_INVALID)
        return

    currency = TransactionCurrency(currency_value)
    currency_name = CURRENCY_NAMES_GENITIVE[currency_value]
    amount = int(raw)
    sender_id = message.from_user.id

    target = await get_user_by_id(session, target_user_id)
    if target is None:
        await message.answer(EXCHANGE_TARGET_GONE)
        return

    async with try_acquire(redis, action_lock(sender_id, LOCK_ACTION_EXCHANGE)) as acquired:
        if not acquired:
            return

        try:
            await clan_service.exchange_currency(
                session, sender_id=sender_id, receiver_id=target.id, amount=amount, currency=currency
            )
        except clan_service.NotInSameClanError:
            await message.answer(EXCHANGE_NOT_IN_CLAN)
            return
        except clan_service.ExchangeNotEnoughCurrencyError as exc:
            await message.answer(EXCHANGE_NOT_ENOUGH.format(currency=currency_name, needed=format_number(exc.needed)))
            return

    display_username = target.username or str(target.id)
    await message.answer(
        EXCHANGE_DONE.format(amount=format_number(amount), currency=currency_name, username=display_username)
    )

    if target.notifications_enabled:
        sender_username = message.from_user.username or str(sender_id)
        await notify(
            bot,
            target.id,
            NOTIFY_EXCHANGE_RECEIVED.format(
                amount=format_number(amount), currency=currency_name, username=sender_username
            ),
        )

    # Возвращаем игрока в меню клана (подтверждено пользователем 2026-08-14) — тот же
    # рендер, что используют остальные экраны клана, новым сообщением (мы отвечаем на
    # текстовое сообщение с числом, редактировать тут нечего).
    sender_member = await clan_repo.get_member(session, sender_id)
    if sender_member is not None:
        await render_clan_card(bot, message.chat.id, session, sender_member)
