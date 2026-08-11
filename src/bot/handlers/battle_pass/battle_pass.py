from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.battle_pass import CB_BATTLE_PASS_OPEN
from bot.db.repositories.user import get_by_id
from bot.handlers.battle_pass.levels import show_page
from bot.texts.common import BTN_PASS, NEED_START

router = Router(name="battle_pass")


@router.message(Command("pass"))
@router.message(F.text == BTN_PASS)
async def show_pass(message: Message, session: AsyncSession) -> None:
    user = await get_by_id(session, message.from_user.id)
    if user is None:
        await message.answer(NEED_START)
        return
    # page=None — открыть сразу на странице с первым незабранным уровнем, а не всегда с
    # начала круга (подтверждено пользователем 2026-08-11, см. CLAUDE.md).
    await show_page(message, session, message.from_user.id, page=None, edit=False)


@router.callback_query(F.data == CB_BATTLE_PASS_OPEN)
async def cb_open_pass(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    await show_page(callback.message, session, callback.from_user.id, page=None, edit=True)
