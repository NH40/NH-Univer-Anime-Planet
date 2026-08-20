from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.constant.admin import CB_ADMIN_SEASON, CB_ADMIN_SEASON_BUMP_VERSION, CB_ADMIN_SEASON_NEW, CB_ADMIN_SEASON_NEW_CONFIRM
from bot.db.repositories import season as season_repo
from bot.keyboards.admin import season_menu, season_new_confirm_menu
from bot.keyboards.common import back_button_menu
from bot.services import broadcast as broadcast_service
from bot.services import season as season_service
from bot.states.admin import AdminStates
from bot.texts.admin import (
    ACTION_CANCELLED,
    SEASON_BUMP_DONE,
    SEASON_BUMP_PROMPT,
    SEASON_CHANGE_BROADCAST,
    SEASON_NEW_CONFIRM,
    SEASON_NEW_DONE,
    SEASON_NEW_PROMPT,
    SEASON_NONE,
    SEASON_SCREEN,
    SEASON_TOP_REWARD_NOTIFY,
    SEASON_VERSION_INVALID,
)
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_season")
log = logging.getLogger(__name__)

_DATE_FMT = "%d.%m.%Y %H:%M"
_MAX_VERSION_LEN = 16

# Держим ссылки на фоновые таски уведомления о смене сезона — тот же приём, что у
# рассылки старта ивента (handlers/admin/events.py): без сохранённой ссылки asyncio может
# собрать таск мусорщиком до завершения.
_season_change_tasks: set[asyncio.Task] = set()


async def _notify_season_change(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    version: str,
    rewards: list[season_service.TopPlayerReward],
) -> None:
    try:
        # Сначала персональные уведомления топ-10 с местом и наградой (короткий список, не
        # нужна батчевая рассылка), потом общее объявление всем игрокам.
        for reward in rewards:
            await notify(
                bot,
                reward.user_id,
                SEASON_TOP_REWARD_NOTIFY.format(
                    place=reward.place, ubp_season=reward.ubp_season, coins=reward.coins, version=version
                ),
            )
        async with session_factory() as session:
            await broadcast_service.run_broadcast(bot, session, SEASON_CHANGE_BROADCAST.format(version=version))
    except Exception:
        log.exception("Season change notification failed")


def _is_valid_version(raw: str) -> bool:
    return 0 < len(raw) <= _MAX_VERSION_LEN


async def _render_season(session: AsyncSession) -> str:
    season = await season_repo.get_active(session)
    if season is None:
        return SEASON_NONE
    return SEASON_SCREEN.format(version=season.version, started_at=season.started_at.strftime(_DATE_FMT))


@router.callback_query(F.data == CB_ADMIN_SEASON)
async def cb_season(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    # Точка возврата "Назад" для waiting_new_season_version/waiting_bump_version (см.
    # CLAUDE.md, 2026-08-21).
    await state.clear()
    await callback.answer()
    text = await _render_season(session)
    await safe_edit_text(callback.message, text, reply_markup=season_menu())


@router.callback_query(F.data == CB_ADMIN_SEASON_NEW)
async def cb_season_new_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_new_season_version)
    await callback.answer()
    await safe_edit_text(callback.message, SEASON_NEW_PROMPT, reply_markup=back_button_menu(CB_ADMIN_SEASON))


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
async def cb_season_new_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    data = await state.get_data()
    version = data.get("new_season_version")
    await state.clear()

    if not version:
        await callback.answer(ACTION_CANCELLED, show_alert=True)
        return

    _new_season, rewards = await season_service.start_new_season(session, version=version)
    await callback.answer(SEASON_NEW_DONE.format(version=version, count=len(rewards)), show_alert=True)

    # Уведомления игрокам — фоновым таском, не await прямо в хендлере (рассылка на 30k
    # игроков растянулась бы на минуты, см. CLAUDE.md, "Рассылка").
    task = asyncio.create_task(_notify_season_change(bot, session_factory, version=version, rewards=rewards))
    _season_change_tasks.add(task)
    task.add_done_callback(_season_change_tasks.discard)

    text = await _render_season(session)
    await safe_edit_text(callback.message, text, reply_markup=season_menu())


@router.callback_query(F.data == CB_ADMIN_SEASON_BUMP_VERSION)
async def cb_season_bump_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.waiting_bump_version)
    await callback.answer()
    await safe_edit_text(callback.message, SEASON_BUMP_PROMPT, reply_markup=back_button_menu(CB_ADMIN_SEASON))


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
