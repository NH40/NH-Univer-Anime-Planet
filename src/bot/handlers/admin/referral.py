from __future__ import annotations

import re

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import CB_ADMIN_REFERRAL, CB_ADMIN_REFERRAL_CREATE, CB_ADMIN_REFERRAL_DETAIL_PREFIX
from bot.keyboards.admin import referral_detail_menu, referral_menu
from bot.keyboards.common import back_button_menu
from bot.services import referral as referral_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    REFERRAL_CHOOSE,
    REFERRAL_CREATE_DONE,
    REFERRAL_CREATE_INVALID,
    REFERRAL_CREATE_PROMPT,
    REFERRAL_CREATE_TAKEN,
    REFERRAL_DETAIL_NOT_FOUND,
    REFERRAL_DETAIL_SCREEN,
    REFERRAL_EMPTY,
    REFERRAL_SCREEN,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_referral")

_CODE_RE = re.compile(r"^[A-Za-z0-9_]{1,32}$")


@router.callback_query(F.data == CB_ADMIN_REFERRAL)
async def cb_referral(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    # Точка возврата "Назад" для waiting_referral_create (см. CLAUDE.md, 2026-08-21).
    await state.clear()
    await callback.answer()
    links = await referral_service.list_links_with_stats(session)
    if not links:
        await safe_edit_text(callback.message, f"{REFERRAL_SCREEN}\n\n{REFERRAL_EMPTY}", reply_markup=referral_menu([]))
        return
    codes = [code for code, _visited, _playing in links]
    await safe_edit_text(callback.message, f"{REFERRAL_SCREEN}\n\n{REFERRAL_CHOOSE}", reply_markup=referral_menu(codes))


@router.callback_query(F.data.startswith(CB_ADMIN_REFERRAL_DETAIL_PREFIX))
async def cb_referral_detail(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    code = callback.data[len(CB_ADMIN_REFERRAL_DETAIL_PREFIX) :]
    stats = await referral_service.get_campaign_stats(session, code)
    await callback.answer()
    if stats is None:
        await callback.message.answer(REFERRAL_DETAIL_NOT_FOUND)
        return

    me = await bot.get_me()
    await safe_edit_text(
        callback.message,
        REFERRAL_DETAIL_SCREEN.format(
            code=stats.code,
            url=f"https://t.me/{me.username}?start=ref_{stats.code}",
            visited=stats.visited,
            playing=stats.playing,
            subscriptions_bought=stats.subscriptions_bought,
            battle_passes_bought=stats.battle_passes_bought,
            donated_coins=stats.donated_coins,
        ),
        reply_markup=referral_detail_menu(),
    )


@router.callback_query(F.data == CB_ADMIN_REFERRAL_CREATE)
async def cb_referral_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_referral_create)
    await callback.answer()
    await safe_edit_text(callback.message, REFERRAL_CREATE_PROMPT, reply_markup=back_button_menu(CB_ADMIN_REFERRAL))


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
