from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import CB_ADMIN_REFERRAL, CB_ADMIN_REFERRAL_CREATE
from bot.keyboards.admin import referral_menu
from bot.services import referral as referral_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    REFERRAL_CREATE_DONE,
    REFERRAL_CREATE_INVALID,
    REFERRAL_CREATE_PROMPT,
    REFERRAL_CREATE_TAKEN,
    REFERRAL_EMPTY,
    REFERRAL_LINE,
    REFERRAL_SCREEN,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_referral")

_CODE_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")


async def _render_referral(bot: Bot, session: AsyncSession) -> str:
    links = await referral_service.list_links_with_stats(session)
    if not links:
        return REFERRAL_SCREEN.format(lines=REFERRAL_EMPTY)

    me = await bot.get_me()
    lines = "".join(
        REFERRAL_LINE.format(code=code, visited=visited, playing=playing, url=f"https://t.me/{me.username}?start=ref_{code}")
        for code, visited, playing in links
    )
    return REFERRAL_SCREEN.format(lines=lines)


@router.callback_query(F.data == CB_ADMIN_REFERRAL)
async def cb_referral(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    await callback.answer()
    text = await _render_referral(bot, session)
    await safe_edit_text(callback.message, text, reply_markup=referral_menu())


@router.callback_query(F.data == CB_ADMIN_REFERRAL_CREATE)
async def cb_referral_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_referral_create)
    await callback.answer()
    await safe_edit_text(callback.message, REFERRAL_CREATE_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_referral_create), Command("cancel"))
async def cancel_referral_create(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_referral_create))
async def apply_referral_create(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    code = (message.text or "").strip()
    if not _CODE_RE.match(code):
        await message.answer(REFERRAL_CREATE_INVALID)
        return

    await state.clear()
    try:
        await referral_service.create_link(session, code=code, admin_id=message.from_user.id)
    except referral_service.ReferralCodeTakenError:
        await message.answer(REFERRAL_CREATE_TAKEN)
        return

    me = await bot.get_me()
    url = f"https://t.me/{me.username}?start=ref_{code}"
    await message.answer(REFERRAL_CREATE_DONE.format(url=url))
