from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import get_settings
from bot.constant.admin import CB_ADMIN_MANAGE_ADMINS, CB_ADMIN_MANAGE_FIND_PLAYER, CB_ADMIN_TOGGLE_ADMIN_PREFIX
from bot.db.models.user import User
from bot.db.repositories.user import get_by_id, list_admins, set_is_admin
from bot.handlers.admin.admin import resolve_player
from bot.keyboards.admin import manage_admin_card_menu, manage_admins_menu
from bot.services.admin import is_config_admin
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    ADMIN_GRANTED,
    ADMIN_REVOKED,
    FIND_PLAYER_NOT_FOUND,
    MANAGE_ADMIN_CARD,
    MANAGE_ADMINS_EMPTY,
    MANAGE_ADMINS_HEADER,
    MANAGE_ADMINS_LINE,
    MANAGE_FIND_PLAYER_PROMPT,
    NOT_SUPER_ADMIN,
    NOTIFY_ADMIN_GRANTED,
    NOTIFY_ADMIN_REVOKED,
)
from bot.texts.settings import STATUS_OFF, STATUS_ON
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_manage")


def _manage_admin_card_text(user: User) -> str:
    status = STATUS_ON if user.is_admin else STATUS_OFF
    username = f" @{user.username}" if user.username else ""
    return MANAGE_ADMIN_CARD.format(name=user.display_name or "—", id=user.id, username=username, status=status)


@router.callback_query(F.data == CB_ADMIN_MANAGE_ADMINS)
async def cb_manage_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    if not is_config_admin(callback.from_user.id, settings):
        await callback.answer(NOT_SUPER_ADMIN, show_alert=True)
        return

    admins = await list_admins(session)
    await callback.answer()

    body = (
        "".join(
            MANAGE_ADMINS_LINE.format(
                name=a.display_name or "—", id=a.id, username=f" @{a.username}" if a.username else ""
            )
            for a in admins
        )
        or MANAGE_ADMINS_EMPTY
    )
    await safe_edit_text(callback.message, MANAGE_ADMINS_HEADER + body, reply_markup=manage_admins_menu())


@router.callback_query(F.data == CB_ADMIN_MANAGE_FIND_PLAYER)
async def cb_manage_find_player_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    settings = get_settings()
    if not is_config_admin(callback.from_user.id, settings):
        await callback.answer(NOT_SUPER_ADMIN, show_alert=True)
        return

    await state.set_state(AdminStates.waiting_manage_admin_search)
    await callback.answer()
    await safe_edit_text(
        callback.message, MANAGE_FIND_PLAYER_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[])
    )


@router.message(StateFilter(AdminStates.waiting_manage_admin_search), Command("cancel"))
async def cancel_manage_find_player(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_manage_admin_search))
async def apply_manage_find_player(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    user = await resolve_player(session, message.text or "")
    if user is None:
        await message.answer(FIND_PLAYER_NOT_FOUND)
        return

    await message.answer(
        _manage_admin_card_text(user), reply_markup=manage_admin_card_menu(user_id=user.id, is_admin=user.is_admin)
    )


@router.callback_query(F.data.startswith(CB_ADMIN_TOGGLE_ADMIN_PREFIX))
async def cb_toggle_admin(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    # Повторная проверка прямо в хендлере, а не только видимостью кнопки в меню — сам
    # callback_data теоретически можно переслать/повторить, а выдача прав слишком
    # чувствительна, чтобы полагаться только на то, что кнопку никто не увидел.
    settings = get_settings()
    if not is_config_admin(callback.from_user.id, settings):
        await callback.answer(NOT_SUPER_ADMIN, show_alert=True)
        return

    target_id = int(callback.data[len(CB_ADMIN_TOGGLE_ADMIN_PREFIX) :])
    target = await get_by_id(session, target_id)
    if target is None:
        await callback.answer(FIND_PLAYER_NOT_FOUND, show_alert=True)
        return

    new_value = not target.is_admin
    await set_is_admin(session, user_id=target_id, enabled=new_value)
    await callback.answer()

    name = target.display_name or "—"
    target.is_admin = new_value  # локально, для рендера карточки — сама запись уже в БД
    await safe_edit_text(
        callback.message,
        (ADMIN_GRANTED if new_value else ADMIN_REVOKED).format(name=name) + "\n\n" + _manage_admin_card_text(target),
        reply_markup=manage_admin_card_menu(user_id=target.id, is_admin=new_value),
    )

    await notify(bot, target.id, NOTIFY_ADMIN_GRANTED if new_value else NOTIFY_ADMIN_REVOKED)
