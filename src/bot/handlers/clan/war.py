from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.config.game import CLAN_WAR_DURATION_HOURS, CLAN_WAR_REWARD_DUST
from bot.constant.clan import CB_CLAN_WAR, CB_CLAN_WAR_START, CB_CLAN_WAR_TARGET_PREFIX, LOCK_ACTION_START_WAR
from bot.db.models.enums import ClanRank, ClanWarStatus
from bot.db.repositories import clan as clan_repo
from bot.handlers.clan.clan import CLAN_PAGE_SIZE
from bot.keyboards.clan import war_menu, war_target_menu
from bot.services import clan as clan_service
from bot.texts.clan import (
    NOT_AUTHORIZED,
    NOT_IN_CLAN,
    WAR_ACTIVE,
    WAR_ALREADY_AT_WAR,
    WAR_FINISHED_DRAW,
    WAR_FINISHED_WIN,
    WAR_NONE,
    WAR_STARTED,
    WAR_TARGET_PROMPT,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_war")

_DATE_FMT = "%d.%m.%Y %H:%M"


async def _render_war(session: AsyncSession, clan_id: int, actor_rank: ClanRank) -> tuple[str, InlineKeyboardMarkup]:
    can_manage = actor_rank in clan_service.MANAGER_RANKS
    war = await clan_repo.get_active_war_for_clan(session, clan_id)
    if war is None:
        return WAR_NONE, war_menu(can_manage=can_manage, has_active_war=False)

    progress = await clan_service.get_progress(session, war)
    clan_a = await clan_repo.get_by_id(session, progress.war.clan_a_id)
    clan_b = await clan_repo.get_by_id(session, progress.war.clan_b_id)

    if progress.war.status == ClanWarStatus.finished:
        if progress.war.winner_clan_id is None:
            text = WAR_FINISHED_DRAW
        else:
            winner = clan_a if progress.war.winner_clan_id == progress.war.clan_a_id else clan_b
            text = WAR_FINISHED_WIN.format(winner=winner.name if winner else "", reward=CLAN_WAR_REWARD_DUST)
        return text, war_menu(can_manage=can_manage, has_active_war=False)

    text = WAR_ACTIVE.format(
        name_a=clan_a.name if clan_a else "",
        gained_a=progress.gained_a,
        name_b=clan_b.name if clan_b else "",
        gained_b=progress.gained_b,
        ends_at=progress.war.ends_at.strftime(_DATE_FMT),
    )
    return text, war_menu(can_manage=can_manage, has_active_war=True)


@router.callback_query(F.data == CB_CLAN_WAR)
async def cb_war(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None:
        await callback.answer(NOT_IN_CLAN, show_alert=True)
        return
    await callback.answer()
    text, keyboard = await _render_war(session, member.clan_id, member.rank)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == CB_CLAN_WAR_START)
async def cb_war_start(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()

    rows, _total_pages = await clan_service.browse_clans(session, by_total=False, page=0, page_size=CLAN_PAGE_SIZE)
    targets = [row for row in rows if row[0].id != member.clan_id]
    await safe_edit_text(callback.message, WAR_TARGET_PROMPT, reply_markup=war_target_menu(targets))


@router.callback_query(F.data.startswith(CB_CLAN_WAR_TARGET_PREFIX))
async def cb_war_target(callback: CallbackQuery, session: AsyncSession, redis: Redis) -> None:
    target_clan_id = int(callback.data[len(CB_CLAN_WAR_TARGET_PREFIX) :])
    actor_id = callback.from_user.id
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return

    async with try_acquire(redis, action_lock(actor_id, LOCK_ACTION_START_WAR)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await clan_service.start_war(session, clan_a_id=member.clan_id, clan_b_id=target_clan_id, actor_id=actor_id)
        except clan_service.WarNotAuthorizedError:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        except clan_service.AlreadyAtWarError:
            await callback.answer(WAR_ALREADY_AT_WAR, show_alert=True)
            return
        await callback.answer()

    target_clan = await clan_repo.get_by_id(session, target_clan_id)
    await callback.message.answer(
        WAR_STARTED.format(target=target_clan.name if target_clan else "", hours=CLAN_WAR_DURATION_HOURS)
    )

    text, keyboard = await _render_war(session, member.clan_id, member.rank)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)
