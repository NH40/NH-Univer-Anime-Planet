from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.constant.admin import CB_ADMIN_BROADCAST_CONFIRM, CB_ADMIN_BROADCAST_START
from bot.db.repositories.user import count_all
from bot.keyboards.admin import broadcast_confirm_menu
from bot.services import broadcast as broadcast_service
from bot.states.admin import AdminStates
from bot.texts.admin import ACTION_CANCELLED, BROADCAST_CONFIRM, BROADCAST_DONE, BROADCAST_PROMPT, BROADCAST_STARTED
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_broadcast")
log = logging.getLogger(__name__)

_PREVIEW_LEN = 50
# Держим ссылки на фоновые таски рассылки — иначе asyncio может собрать их мусорщиком
# посреди выполнения (create_task без сохранённой ссылки не гарантирует завершение).
_background_tasks: set[asyncio.Task] = set()


async def _run_and_report(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], text: str, admin_chat_id: int
) -> None:
    try:
        async with session_factory() as session:
            sent, failed = await broadcast_service.run_broadcast(bot, session, text)
    except Exception:
        log.exception("Broadcast failed")
        return

    preview = text if len(text) <= _PREVIEW_LEN else text[: _PREVIEW_LEN - 1] + "…"
    await notify(bot, admin_chat_id, BROADCAST_DONE.format(preview=preview, sent=sent, failed=failed))


@router.callback_query(F.data == CB_ADMIN_BROADCAST_START)
async def cb_broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_broadcast_text)
    await callback.answer()
    await safe_edit_text(callback.message, BROADCAST_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_broadcast_text), Command("cancel"))
async def cancel_broadcast(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_broadcast_text))
async def apply_broadcast_text(message: Message, state: FSMContext, session: AsyncSession) -> None:
    text = (message.text or "").strip()
    if not text:
        return

    await state.update_data(broadcast_text=text)
    count = await count_all(session)
    await message.answer(BROADCAST_CONFIRM.format(count=count, text=text), reply_markup=broadcast_confirm_menu())


@router.callback_query(F.data == CB_ADMIN_BROADCAST_CONFIRM)
async def cb_broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = await state.get_data()
    text = data.get("broadcast_text")
    await state.clear()

    if not text:
        await callback.answer(ACTION_CANCELLED, show_alert=True)
        return

    count = await count_all(session)
    await callback.answer(BROADCAST_STARTED.format(count=count), show_alert=True)

    task = asyncio.create_task(_run_and_report(bot, session_factory, text, callback.from_user.id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
