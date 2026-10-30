from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, LabeledPrice, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import DONATE_COINS_PER_RUB, DONATE_MAX_RUB, DONATE_MIN_RUB, SBP_PAYMENT_WAIT_MINUTES
from bot.config.settings import get_settings
from bot.constant.donate import (
    CB_DONATE_CARD_PREFIX,
    CB_DONATE_CUSTOM,
    CB_DONATE_OPEN,
    CB_DONATE_PRESET_PREFIX,
    CB_DONATE_SBP_CHECK_PREFIX,
    CB_DONATE_SBP_PREFIX,
    LOCK_ACTION_DONATE_SBP,
    SBP_STATUS_CANCELED,
    SBP_STATUS_SUCCEEDED,
)
from bot.db.repositories import sbp_payment as sbp_repo
from bot.db.repositories.user import get_by_id
from bot.keyboards.common import back_button_menu
from bot.keyboards.donate import back_to_donate, donate_menu, method_menu, sbp_menu
from bot.services import sbp as sbp_service
from bot.states.donate import DonateStates
from bot.texts.common import BTN_DONATE, NEED_START
from bot.texts.donate import (
    DONATE_CANCELLED,
    DONATE_CUSTOM_INVALID,
    DONATE_CUSTOM_PROMPT,
    DONATE_INVOICE_DESCRIPTION,
    DONATE_INVOICE_LABEL,
    DONATE_INVOICE_TITLE,
    DONATE_METHOD_SCREEN,
    DONATE_NOT_CONFIGURED,
    DONATE_SBP_ALREADY,
    DONATE_SBP_BUSY,
    DONATE_SBP_CANCELED_SCREEN,
    DONATE_SBP_DONE_ALERT,
    DONATE_SBP_FAILED,
    DONATE_SBP_PAID_SCREEN,
    DONATE_SBP_SCREEN,
    DONATE_SBP_WAITING,
    DONATE_SCREEN,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="donate")

_KOPECKS_PER_RUB = 100


async def _send_invoice(bot: Bot, chat_id: int, amount_rub: int) -> None:
    settings = get_settings()
    await bot.send_invoice(
        chat_id=chat_id,
        title=DONATE_INVOICE_TITLE,
        description=DONATE_INVOICE_DESCRIPTION.format(amount=amount_rub),
        payload=f"donate:{amount_rub}",
        provider_token=settings.yookassa_provider_token,
        currency="RUB",
        prices=[LabeledPrice(label=DONATE_INVOICE_LABEL.format(amount=amount_rub), amount=amount_rub * _KOPECKS_PER_RUB)],
    )


def _methods() -> tuple[bool, bool]:
    """(СБП доступна, карта через Telegram доступна)."""
    return sbp_service.enabled(), bool(get_settings().yookassa_provider_token)


def _amount(raw: str) -> int | None:
    return int(raw) if raw.isdigit() and DONATE_MIN_RUB <= int(raw) <= DONATE_MAX_RUB else None


@router.message(Command("donate"))
@router.message(F.text == BTN_DONATE)
async def show_donate(message: Message, session: AsyncSession) -> None:
    user = await get_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return
    await message.answer(DONATE_SCREEN.format(coins=user.coins), reply_markup=donate_menu())


@router.callback_query(F.data == CB_DONATE_OPEN)
async def cb_donate_open(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    # Точка возврата "Назад" для флоу ввода своей суммы (см. CLAUDE.md, 2026-08-21).
    await state.clear()
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return
    await callback.answer()
    await safe_edit_text(callback.message, DONATE_SCREEN.format(coins=user.coins), reply_markup=donate_menu())


@router.callback_query(F.data.startswith(CB_DONATE_PRESET_PREFIX))
async def cb_donate_preset(callback: CallbackQuery, bot: Bot) -> None:
    sbp, card = _methods()
    amount_rub = _amount(callback.data[len(CB_DONATE_PRESET_PREFIX) :])
    if not (sbp or card) or amount_rub is None:
        await callback.answer(DONATE_NOT_CONFIGURED, show_alert=True)
        return
    await callback.answer()
    if not sbp:  # только карта — как было до СБП: сразу инвойс
        await _send_invoice(bot, callback.message.chat.id, amount_rub)
        return
    await safe_edit_text(
        callback.message, DONATE_METHOD_SCREEN.format(amount=amount_rub), reply_markup=method_menu(amount_rub, sbp, card)
    )


@router.callback_query(F.data.startswith(CB_DONATE_CARD_PREFIX))
async def cb_donate_card(callback: CallbackQuery, bot: Bot) -> None:
    amount_rub = _amount(callback.data[len(CB_DONATE_CARD_PREFIX) :])
    if not get_settings().yookassa_provider_token or amount_rub is None:
        await callback.answer(DONATE_NOT_CONFIGURED, show_alert=True)
        return
    await callback.answer()
    await _send_invoice(bot, callback.message.chat.id, amount_rub)


@router.callback_query(F.data.startswith(CB_DONATE_SBP_PREFIX))
async def cb_donate_sbp(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    amount_rub = _amount(callback.data[len(CB_DONATE_SBP_PREFIX) :])
    if not sbp_service.enabled() or amount_rub is None:
        await callback.answer(DONATE_NOT_CONFIGURED, show_alert=True)
        return
    if await get_by_id(session, callback.from_user.id) is None:
        await callback.answer(NEED_START, show_alert=True)
        return
    # Правило 2: двойной тап не должен завести два счёта.
    async with try_acquire(redis, action_lock(callback.from_user.id, LOCK_ACTION_DONATE_SBP), ttl_ms=20000) as acquired:
        if not acquired:
            await callback.answer(DONATE_SBP_BUSY)
            return
        try:
            row = await sbp_service.create(session, bot, callback.from_user.id, amount_rub)
        except sbp_service.YooKassaError:
            await callback.answer(DONATE_SBP_FAILED, show_alert=True)
            return
    await callback.answer()
    await safe_edit_text(
        callback.message,
        DONATE_SBP_SCREEN.format(amount=amount_rub, minutes=SBP_PAYMENT_WAIT_MINUTES),
        reply_markup=sbp_menu(row.id, amount_rub, row.confirmation_url),
    )
    await sbp_service.attach_message(session, row, callback.message.chat.id, callback.message.message_id)


@router.callback_query(F.data.startswith(CB_DONATE_SBP_CHECK_PREFIX))
async def cb_donate_sbp_check(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    raw = callback.data[len(CB_DONATE_SBP_CHECK_PREFIX) :]
    row = await sbp_repo.get(session, int(raw)) if raw.isdigit() else None
    if row is None or row.user_id != callback.from_user.id:
        await callback.answer()
        return
    async with try_acquire(redis, action_lock(callback.from_user.id, LOCK_ACTION_DONATE_SBP), ttl_ms=20000) as acquired:
        if not acquired:
            await callback.answer(DONATE_SBP_BUSY)
            return
        try:
            status, result = await sbp_service.refresh(session, row)
        except sbp_service.YooKassaError:
            await callback.answer(DONATE_SBP_WAITING, show_alert=True)
            return
    if result is not None:
        await callback.answer(DONATE_SBP_DONE_ALERT, show_alert=True)
        await sbp_service.announce(bot, result)
    elif status == SBP_STATUS_SUCCEEDED:
        await callback.answer(DONATE_SBP_ALREADY, show_alert=True)
        await safe_edit_text(
            callback.message, DONATE_SBP_PAID_SCREEN.format(amount=row.amount_rub, coins=row.amount_rub * DONATE_COINS_PER_RUB),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
        )
    elif status == SBP_STATUS_CANCELED:
        await callback.answer()
        await safe_edit_text(callback.message, DONATE_SBP_CANCELED_SCREEN, reply_markup=back_to_donate())
    else:
        await callback.answer(DONATE_SBP_WAITING, show_alert=True)


@router.callback_query(F.data == CB_DONATE_CUSTOM)
async def cb_donate_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not any(_methods()):
        await callback.answer(DONATE_NOT_CONFIGURED, show_alert=True)
        return
    await state.set_state(DonateStates.waiting_amount)
    await callback.answer()
    await callback.message.answer(
        DONATE_CUSTOM_PROMPT.format(min=DONATE_MIN_RUB, max=DONATE_MAX_RUB),
        reply_markup=back_button_menu(CB_DONATE_OPEN),
    )


@router.message(StateFilter(DonateStates.waiting_amount), Command("cancel"))
async def cancel_custom_amount(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(DONATE_CANCELLED)


@router.message(StateFilter(DonateStates.waiting_amount))
async def apply_custom_amount(message: Message, state: FSMContext, bot: Bot) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (DONATE_MIN_RUB <= int(raw) <= DONATE_MAX_RUB):
        await message.answer(DONATE_CUSTOM_INVALID.format(min=DONATE_MIN_RUB, max=DONATE_MAX_RUB))
        return

    await state.clear()
    amount_rub = int(raw)
    sbp, card = _methods()
    if not sbp:
        await _send_invoice(bot, message.chat.id, amount_rub)
        return
    await message.answer(DONATE_METHOD_SCREEN.format(amount=amount_rub), reply_markup=method_menu(amount_rub, sbp, card))
