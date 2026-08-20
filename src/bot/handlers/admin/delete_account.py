from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX, CB_ADMIN_DELETE_ACCOUNT_START, CB_ADMIN_OPEN
from bot.handlers.admin.admin import resolve_player
from bot.keyboards.admin import delete_account_confirm_menu
from bot.keyboards.common import back_button_menu
from bot.services import admin as admin_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    DELETE_ACCOUNT_CONFIRM,
    DELETE_ACCOUNT_DONE,
    DELETE_ACCOUNT_OWNER_BLOCKED,
    DELETE_ACCOUNT_PROMPT,
    FIND_PLAYER_NOT_FOUND,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_delete_account")


@router.callback_query(F.data == CB_ADMIN_DELETE_ACCOUNT_START)
async def cb_delete_account_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_delete_account)
    await callback.answer()
    await safe_edit_text(callback.message, DELETE_ACCOUNT_PROMPT, reply_markup=back_button_menu(CB_ADMIN_OPEN))


@router.message(StateFilter(AdminStates.waiting_delete_account), Command("cancel"))
async def cancel_delete_account(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_delete_account))
async def apply_delete_account_find(message: Message, state: FSMContext, session: AsyncSession) -> None:
    user = await resolve_player(session, message.text or "")
    if user is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await state.clear()
    name = user.display_name or str(user.id)
    await message.answer(
        DELETE_ACCOUNT_CONFIRM.format(name=name, id=user.id), reply_markup=delete_account_confirm_menu(user.id)
    )


@router.callback_query(F.data.startswith(CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX))
async def cb_delete_account_confirm(callback: CallbackQuery, session: AsyncSession) -> None:
    target_id = int(callback.data[len(CB_ADMIN_DELETE_ACCOUNT_CONFIRM_PREFIX) :])
    user = await resolve_player(session, str(target_id))
    if user is None:
        await callback.answer(FIND_PLAYER_NOT_FOUND, show_alert=True)
        return

    name = user.display_name or str(user.id)
    try:
        await admin_service.delete_account(session, user_id=target_id)
    except admin_service.OwnerBlockedError as exc:
        await callback.answer(DELETE_ACCOUNT_OWNER_BLOCKED.format(name=name, clan_name=exc.clan_name), show_alert=True)
        return

    await callback.answer(DELETE_ACCOUNT_DONE.format(name=name, id=target_id), show_alert=True)
    await safe_edit_text(callback.message, DELETE_ACCOUNT_DONE.format(name=name, id=target_id))
