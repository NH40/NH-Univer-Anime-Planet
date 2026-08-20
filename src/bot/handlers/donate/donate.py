from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DONATE_MAX_RUB, DONATE_MIN_RUB
from bot.config.settings import get_settings
from bot.constant.donate import CB_DONATE_CUSTOM, CB_DONATE_OPEN, CB_DONATE_PRESET_PREFIX
from bot.db.repositories.user import get_by_id
from bot.keyboards.common import back_button_menu
from bot.keyboards.donate import donate_menu
from bot.states.donate import DonateStates
from bot.texts.common import BTN_DONATE, NEED_START
from bot.texts.donate import (
    DONATE_CANCELLED,
    DONATE_CUSTOM_INVALID,
    DONATE_CUSTOM_PROMPT,
    DONATE_INVOICE_DESCRIPTION,
    DONATE_INVOICE_LABEL,
    DONATE_INVOICE_TITLE,
    DONATE_NOT_CONFIGURED,
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
    if not get_settings().yookassa_provider_token:
        await callback.answer(DONATE_NOT_CONFIGURED, show_alert=True)
        return
    amount_rub = int(callback.data[len(CB_DONATE_PRESET_PREFIX) :])
    await callback.answer()
    await _send_invoice(bot, callback.message.chat.id, amount_rub)


@router.callback_query(F.data == CB_DONATE_CUSTOM)
async def cb_donate_custom_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not get_settings().yookassa_provider_token:
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
    await _send_invoice(bot, message.chat.id, int(raw))
