from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.admin import CB_ADMIN_SEASON, CB_ADMIN_SEASON_BUMP_VERSION, CB_ADMIN_SEASON_NEW, CB_ADMIN_SEASON_NEW_CONFIRM
from bot.db.repositories import season as season_repo
from bot.keyboards.admin import season_menu, season_new_confirm_menu
from bot.services import season as season_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    SEASON_BUMP_DONE,
    SEASON_BUMP_PROMPT,
    SEASON_NEW_CONFIRM,
    SEASON_NEW_DONE,
    SEASON_NEW_PROMPT,
    SEASON_NONE,
    SEASON_SCREEN,
    SEASON_VERSION_INVALID,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_season")

_DATE_FMT = "%d.%m.%Y %H:%M"
_MAX_VERSION_LEN = 16


def _is_valid_version(raw: str) -> bool:
    return 0 < len(raw) <= _MAX_VERSION_LEN


async def _render_season(session: AsyncSession) -> str:
    season = await season_repo.get_active(session)
    if season is None:
        return SEASON_NONE
    return SEASON_SCREEN.format(version=season.version, started_at=season.started_at.strftime(_DATE_FMT))


@router.callback_query(F.data == CB_ADMIN_SEASON)
async def cb_season(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    text = await _render_season(session)
    await safe_edit_text(callback.message, text, reply_markup=season_menu())


@router.callback_query(F.data == CB_ADMIN_SEASON_NEW)
async def cb_season_new_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_new_season_version)
    await callback.answer()
    await safe_edit_text(callback.message, SEASON_NEW_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_new_season_version), Command("cancel"))
async def cancel_season_new(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_new_season_version))
async def apply_season_new_version(message: Message, state: FSMContext) -> None:
    version = (message.text or "").strip()
    if not _is_valid_version(version):
        await message.answer(SEASON_VERSION_INVALID)
        return

    await state.update_data(new_season_version=version)
    await message.answer(SEASON_NEW_CONFIRM.format(version=version), reply_markup=season_new_confirm_menu())


@router.callback_query(F.data == CB_ADMIN_SEASON_NEW_CONFIRM)
async def cb_season_new_confirm(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    data = await state.get_data()
    version = data.get("new_season_version")
    await state.clear()

    if not version:
        await callback.answer(ACTION_CANCELLED, show_alert=True)
        return

    _new_season, rewards = await season_service.start_new_season(session, version=version)
    await callback.answer(SEASON_NEW_DONE.format(version=version, count=len(rewards)), show_alert=True)

    text = await _render_season(session)
    await safe_edit_text(callback.message, text, reply_markup=season_menu())


@router.callback_query(F.data == CB_ADMIN_SEASON_BUMP_VERSION)
async def cb_season_bump_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_bump_version)
    await callback.answer()
    await safe_edit_text(callback.message, SEASON_BUMP_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(AdminStates.waiting_bump_version), Command("cancel"))
async def cancel_season_bump(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(AdminStates.waiting_bump_version))
async def apply_season_bump_version(message: Message, state: FSMContext, session: AsyncSession) -> None:
    version = (message.text or "").strip()
    if not _is_valid_version(version):
        await message.answer(SEASON_VERSION_INVALID)
        return

    await state.clear()
    try:
        await season_service.bump_version(session, version=version)
    except season_service.NoActiveSeasonError:
        await message.answer(SEASON_NONE)
        return

    await message.answer(SEASON_BUMP_DONE.format(version=version))
