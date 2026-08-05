from __future__ import annotations

import math

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import get_count, get_page, get_rank, get_top
from bot.config.game import TICKET_NATURAL_CAP
from bot.constant.profile import (
    CB_PLAYERS_PAGE_PREFIX,
    CB_PROFILE_DAILY_BONUS,
    CB_PROFILE_REFERRALS,
    CB_PROFILE_RENAME,
)
from bot.db.repositories.clan import get_name as get_clan_name
from bot.db.repositories.inventory import UniverseProgress, get_universe_progress
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.user import get_by_id, get_many_by_ids, set_display_name
from bot.keyboards.profile import players_pager, profile_menu
from bot.services import ticket
from bot.states.profile import ProfileStates
from bot.texts.common import BTN_PROFILE, NEED_START
from bot.texts.profile import (
    NO_CLAN,
    NO_RANK,
    NO_USERNAME,
    PLAYERS_EMPTY,
    PLAYERS_HEADER,
    PLAYERS_LINE,
    PROFILE_CARD,
    PROGRESS_EMPTY,
    PROGRESS_HEADER,
    PROGRESS_LINE,
    RENAME_CANCELLED,
    RENAME_DONE,
    RENAME_INVALID,
    RENAME_PROMPT,
    STUB_DAILY_BONUS,
    STUB_REFERRALS,
    TICKETS_LINE_COUNTDOWN,
    TICKETS_LINE_READY,
    TOP_EMPTY,
    TOP_HEADER,
    TOP_LINE,
)
from bot.utils.formatting import esc, progress_bar
from bot.utils.safe_edit import safe_edit_text

router = Router(name="profile")

PLAYERS_PAGE_SIZE = 20


def _tickets_line(status: ticket.TicketStatus) -> str:
    if status.seconds_until_next is None:
        return TICKETS_LINE_READY.format(count=status.count, cap=TICKET_NATURAL_CAP)
    mm, ss = divmod(status.seconds_until_next, 60)
    return TICKETS_LINE_COUNTDOWN.format(count=status.count, cap=TICKET_NATURAL_CAP, mm=mm, ss=ss)


def _progress_block(progress: list[UniverseProgress]) -> str:
    if not any(p.owned for p in progress):
        return PROGRESS_EMPTY
    lines = "".join(
        PROGRESS_LINE.format(
            universe=esc(p.title), bar=progress_bar(p.percent), percent=p.percent, owned=p.owned, total=p.total
        )
        for p in progress
    )
    return PROGRESS_HEADER + lines


async def _render_profile(session: AsyncSession, redis: Redis, user_id: int) -> str | None:
    user = await get_by_id(session, user_id)
    if user is None:
        return None

    clan_name = await get_clan_name(session, user.clan_id)
    season = await get_active_season(session)
    rank = await get_rank(redis, season.id, user_id) if season else None
    ticket_status = await ticket.get_status(session, user_id)
    progress = await get_universe_progress(session, user_id)
    await session.commit()  # get_status могла применить лениво накопленный реген тикетов

    return PROFILE_CARD.format(
        name=esc(user.display_name or "—"),
        username=f"@{esc(user.username)}" if user.username else NO_USERNAME,
        clan=esc(clan_name) if clan_name else NO_CLAN,
        ubp_season=user.ubp_season,
        rank=rank if rank else NO_RANK,
        ubp_total=user.ubp_total,
        tickets_line=_tickets_line(ticket_status),
        total_rolls=user.total_rolls,
        progress=_progress_block(progress),
    )


@router.message(Command("profile"))
@router.message(F.text == BTN_PROFILE)
async def show_profile(message: Message, session: AsyncSession, redis: Redis) -> None:
    text = await _render_profile(session, redis, message.from_user.id)
    if text is None:
        await message.answer(NEED_START)
        return
    await message.answer(text, reply_markup=profile_menu())


@router.callback_query(F.data == CB_PROFILE_RENAME)
async def cb_rename_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ProfileStates.waiting_new_name)
    await callback.answer()
    await callback.message.answer(RENAME_PROMPT)


@router.callback_query(F.data == CB_PROFILE_REFERRALS)
async def cb_referrals_stub(callback: CallbackQuery) -> None:
    """Заглушка — см. TODO.md, план реализации рефералов в профиле."""
    await callback.answer(STUB_REFERRALS, show_alert=True)


@router.callback_query(F.data == CB_PROFILE_DAILY_BONUS)
async def cb_daily_bonus_stub(callback: CallbackQuery) -> None:
    """Заглушка — см. TODO.md, план реализации ежедневного бонуса."""
    await callback.answer(STUB_DAILY_BONUS, show_alert=True)


@router.message(StateFilter(ProfileStates.waiting_new_name), Command("cancel"))
async def cancel_rename(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(RENAME_CANCELLED)


@router.message(StateFilter(ProfileStates.waiting_new_name))
async def apply_rename(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = (message.text or "").strip()
    if not (2 <= len(name) <= 32) or "\n" in name:
        await message.answer(RENAME_INVALID)
        return

    await set_display_name(session, user_id=message.from_user.id, display_name=name)
    await state.clear()
    await message.answer(RENAME_DONE.format(name=esc(name)))


@router.message(Command("top"))
async def cmd_top(message: Message, session: AsyncSession, redis: Redis) -> None:
    season = await get_active_season(session)
    if season is None:
        await message.answer(TOP_EMPTY)
        return

    top = await get_top(redis, session, season.id, 10)
    if not top:
        await message.answer(TOP_EMPTY)
        return

    users = await get_many_by_ids(session, [uid for uid, _ in top])
    lines = "".join(
        TOP_LINE.format(place=i + 1, name=esc(users[uid].display_name or "—"), ubp=ubp)
        for i, (uid, ubp) in enumerate(top)
        if uid in users
    )
    await message.answer(TOP_HEADER + lines)


async def _render_players_page(session: AsyncSession, redis: Redis, page: int) -> tuple[str, int]:
    season = await get_active_season(session)
    if season is None:
        return PLAYERS_EMPTY, 1

    total = await get_count(redis, session, season.id)
    if total == 0:
        return PLAYERS_EMPTY, 1

    total_pages = max(1, math.ceil(total / PLAYERS_PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))
    start = page * PLAYERS_PAGE_SIZE
    end = start + PLAYERS_PAGE_SIZE - 1

    rows = await get_page(redis, session, season.id, start, end)
    users = await get_many_by_ids(session, [uid for uid, _ in rows])
    lines = "".join(
        PLAYERS_LINE.format(
            place=start + i + 1,
            name=esc(users[uid].display_name or "—"),
            username=esc(users[uid].username) if users[uid].username else "—",
            ubp=ubp,
        )
        for i, (uid, ubp) in enumerate(rows)
        if uid in users
    )
    return PLAYERS_HEADER.format(page=page + 1, total_pages=total_pages) + lines, total_pages


@router.message(Command("players"))
async def cmd_players(message: Message, session: AsyncSession, redis: Redis) -> None:
    text, total_pages = await _render_players_page(session, redis, 0)
    await message.answer(text, reply_markup=players_pager(0, total_pages))


@router.callback_query(F.data.startswith(CB_PLAYERS_PAGE_PREFIX))
async def cb_players_page(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    page = int(callback.data[len(CB_PLAYERS_PAGE_PREFIX) :])
    text, total_pages = await _render_players_page(session, redis, page)
    await callback.answer()
    await safe_edit_text(callback.message, text, reply_markup=players_pager(page, total_pages))
