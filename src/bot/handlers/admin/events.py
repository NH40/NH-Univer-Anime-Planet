from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import EVENT_CARD_CHANCE
from bot.constant.admin import CB_ADMIN_EVENT_TOGGLE_PREFIX, CB_ADMIN_EVENTS
from bot.keyboards.admin import events_menu
from bot.services import event as event_service
from bot.texts.admin import EVENT_ACTIVE_ICON, EVENT_INACTIVE_ICON, EVENT_STATUS_LINE, EVENT_TOGGLED_OFF, EVENT_TOGGLED_ON, EVENTS_HEADER
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_events")


def _screen_text(statuses: list[event_service.EventStatus]) -> str:
    body = "".join(
        EVENT_STATUS_LINE.format(icon=EVENT_ACTIVE_ICON if s.is_active else EVENT_INACTIVE_ICON, title=s.title)
        for s in statuses
    )
    return EVENTS_HEADER.format(chance=EVENT_CARD_CHANCE * 100) + body


@router.callback_query(F.data == CB_ADMIN_EVENTS)
async def cb_events_open(callback: CallbackQuery, session: AsyncSession) -> None:
    statuses = await event_service.list_status(session)
    await callback.answer()
    await safe_edit_text(callback.message, _screen_text(statuses), reply_markup=events_menu(statuses))


@router.callback_query(F.data.startswith(CB_ADMIN_EVENT_TOGGLE_PREFIX))
async def cb_event_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    code = callback.data[len(CB_ADMIN_EVENT_TOGGLE_PREFIX) :]
    statuses = await event_service.list_status(session)
    current = next((s for s in statuses if s.code == code), None)
    if current is None:
        await callback.answer()
        return

    new_value = not current.is_active
    await event_service.set_active(session, code=code, active=new_value)
    await callback.answer((EVENT_TOGGLED_ON if new_value else EVENT_TOGGLED_OFF).format(title=current.title))

    statuses = await event_service.list_status(session)
    await safe_edit_text(callback.message, _screen_text(statuses), reply_markup=events_menu(statuses))
