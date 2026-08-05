from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.settings import (
    CB_SET_UNIVERSE_PREFIX,
    CB_SETTINGS_NOTIFICATIONS_OPEN,
    CB_SETTINGS_OPEN,
    CB_SETTINGS_TOGGLE_CLAN_REQUESTS,
    CB_SETTINGS_TOGGLE_ROLL_REMINDER,
    CB_SETTINGS_TOGGLE_TICKETS_FULL,
    CB_SETTINGS_UNIVERSE_OPEN,
)
from bot.db.models.user import User
from bot.db.repositories.universe import get_by_code, list_active
from bot.db.repositories.user import (
    get_by_id,
    set_notify_clan_requests,
    set_notify_roll_reminder,
    set_notify_tickets_full,
    set_universe,
)
from bot.keyboards.settings import notifications_menu, settings_menu, universe_picker
from bot.texts.common import BTN_SETTINGS, NEED_START
from bot.texts.settings import CHOOSE_UNIVERSE, NOTIFICATIONS_MENU, SETTINGS_MENU, UNIVERSES_EMPTY, UNIVERSE_SAVED
from bot.utils.safe_edit import safe_edit_text

router = Router(name="settings")


def _notifications_keyboard(user: User) -> InlineKeyboardMarkup:
    return notifications_menu(
        tickets_full=user.notify_tickets_full,
        roll_reminder=user.notify_roll_reminder,
        clan_requests=user.notify_clan_requests,
    )


@router.message(Command("settings"))
@router.message(F.text == BTN_SETTINGS)
async def cmd_settings(message: Message) -> None:
    await message.answer(SETTINGS_MENU, reply_markup=settings_menu())


@router.callback_query(F.data == CB_SETTINGS_OPEN)
async def cb_settings_open(callback: CallbackQuery) -> None:
    await callback.answer()
    await safe_edit_text(callback.message, SETTINGS_MENU, reply_markup=settings_menu())


@router.callback_query(F.data == CB_SETTINGS_UNIVERSE_OPEN)
async def cb_universe_open(callback: CallbackQuery, session: AsyncSession) -> None:
    universes = await list_active(session)
    await callback.answer()
    if not universes:
        await safe_edit_text(callback.message, UNIVERSES_EMPTY)
        return
    await safe_edit_text(callback.message, CHOOSE_UNIVERSE, reply_markup=universe_picker(universes))


@router.callback_query(F.data.startswith(CB_SET_UNIVERSE_PREFIX))
async def cb_set_universe(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_SET_UNIVERSE_PREFIX) :]
    universe = await get_by_code(session, code)
    if universe is None or not universe.is_active:
        await callback.answer("Вселенная недоступна.", show_alert=True)
        return

    await set_universe(session, user_id=callback.from_user.id, universe_code=code)
    await callback.answer()
    await safe_edit_text(callback.message, UNIVERSE_SAVED.format(title=universe.title))


@router.callback_query(F.data == CB_SETTINGS_NOTIFICATIONS_OPEN)
async def cb_notifications_open(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    await callback.answer()
    if user is None:
        await callback.message.answer(NEED_START)
        return
    await safe_edit_text(callback.message, NOTIFICATIONS_MENU, reply_markup=_notifications_keyboard(user))


@router.callback_query(F.data == CB_SETTINGS_TOGGLE_TICKETS_FULL)
async def cb_toggle_tickets_full(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return

    new_value = not user.notify_tickets_full
    await set_notify_tickets_full(session, user_id=callback.from_user.id, enabled=new_value)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        NOTIFICATIONS_MENU,
        reply_markup=notifications_menu(
            tickets_full=new_value, roll_reminder=user.notify_roll_reminder, clan_requests=user.notify_clan_requests
        ),
    )


@router.callback_query(F.data == CB_SETTINGS_TOGGLE_ROLL_REMINDER)
async def cb_toggle_roll_reminder(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return

    new_value = not user.notify_roll_reminder
    await set_notify_roll_reminder(session, user_id=callback.from_user.id, enabled=new_value)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        NOTIFICATIONS_MENU,
        reply_markup=notifications_menu(
            tickets_full=user.notify_tickets_full, roll_reminder=new_value, clan_requests=user.notify_clan_requests
        ),
    )


@router.callback_query(F.data == CB_SETTINGS_TOGGLE_CLAN_REQUESTS)
async def cb_toggle_clan_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await get_by_id(session, callback.from_user.id)
    if user is None:
        await callback.answer(NEED_START, show_alert=True)
        return

    new_value = not user.notify_clan_requests
    await set_notify_clan_requests(session, user_id=callback.from_user.id, enabled=new_value)
    await callback.answer()
    await safe_edit_text(
        callback.message,
        NOTIFICATIONS_MENU,
        reply_markup=notifications_menu(
            tickets_full=user.notify_tickets_full, roll_reminder=user.notify_roll_reminder, clan_requests=new_value
        ),
    )
