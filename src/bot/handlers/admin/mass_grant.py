from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import (
    CB_ADMIN_MASS_GRANT,
    CB_ADMIN_MASS_GRANT_CONFIRM,
    CB_ADMIN_MASS_GRANT_COINS,
    CB_ADMIN_MASS_GRANT_DUST,
    CB_ADMIN_MASS_GRANT_TICKETS,
)
from bot.db.repositories.user import count_all
from bot.keyboards.admin import mass_grant_confirm_menu, mass_grant_menu
from bot.services import admin as admin_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    CURRENCY_COINS,
    CURRENCY_DUST,
    CURRENCY_TICKETS,
    GIVE_AMOUNT_INVALID,
    MASS_GRANT_AMOUNT_PROMPT,
    MASS_GRANT_CONFIRM,
    MASS_GRANT_DONE,
    MASS_GRANT_SCREEN,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_mass_grant")

_CURRENCY_LABELS = {"dust": CURRENCY_DUST, "coins": CURRENCY_COINS, "tickets": CURRENCY_TICKETS}
_GRANT_FUNCS = {
    "dust": admin_service.mass_grant_dust,
    "coins": admin_service.mass_grant_coins,
    "tickets": admin_service.mass_grant_tickets,
}
_CURRENCY_BY_CALLBACK = {
    CB_ADMIN_MASS_GRANT_DUST: "dust",
    CB_ADMIN_MASS_GRANT_COINS: "coins",
    CB_ADMIN_MASS_GRANT_TICKETS: "tickets",
}


@router.callback_query(F.data == CB_ADMIN_MASS_GRANT)
async def cb_mass_grant(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, MASS_GRANT_SCREEN, reply_markup=mass_grant_menu())


@router.callback_query(F.data.in_(_CURRENCY_BY_CALLBACK))
async def cb_mass_grant_pick_currency(callback: CallbackQuery, state: FSMContext) -> None:
    currency = _CURRENCY_BY_CALLBACK[callback.data]
    await state.set_state(AdminStates.waiting_mass_grant_amount)
    await state.update_data(mass_grant_currency=currency)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        MASS_GRANT_AMOUNT_PROMPT.format(currency=_CURRENCY_LABELS[currency]),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[]),
    )


@router.message(StateFilter(AdminStates.waiting_mass_grant_amount), Command("cancel"))
async def cancel_mass_grant(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_mass_grant_amount))
async def apply_mass_grant_amount(message: Message, state: FSMContext, session: AsyncSession) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(GIVE_AMOUNT_INVALID)
        return

    amount = int(raw)
    data = await state.get_data()
    currency = data.get("mass_grant_currency")
    await state.update_data(mass_grant_amount=amount)

    count = await count_all(session)
    await message.answer(
        MASS_GRANT_CONFIRM.format(amount=amount, currency=_CURRENCY_LABELS[currency], count=count),
        reply_markup=mass_grant_confirm_menu(),
    )


@router.callback_query(F.data == CB_ADMIN_MASS_GRANT_CONFIRM)
async def cb_mass_grant_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    currency = data.get("mass_grant_currency")
    amount = data.get("mass_grant_amount")
    await state.clear()

    if currency is None or amount is None:
        await callback.answer(ACTION_CANCELLED, show_alert=True)
        return

    count = await _GRANT_FUNCS[currency](session, amount=amount, admin_id=callback.from_user.id)
    await callback.answer(
        MASS_GRANT_DONE.format(amount=amount, currency=_CURRENCY_LABELS[currency], count=count), show_alert=True
    )
    await safe_edit_text(callback.message, MASS_GRANT_SCREEN, reply_markup=mass_grant_menu())
