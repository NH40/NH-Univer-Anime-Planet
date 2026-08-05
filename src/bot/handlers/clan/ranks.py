from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.clan import (
    CB_CLAN_RANKS,
    CB_CLAN_SET_RANK_PREFIX,
    CB_CLAN_TRANSFER_CONFIRM_PREFIX,
    CB_CLAN_TRANSFER_START,
    LOCK_ACTION_TRANSFER_OWNERSHIP,
)
from bot.db.models.enums import ClanRank
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.handlers.clan.clan import render_clan_card
from bot.keyboards.clan import rank_set_menu, ranks_menu, transfer_confirm_menu, transfer_menu
from bot.services import clan as clan_service
from bot.texts.clan import (
    NOT_AUTHORIZED,
    RANKS_HEADER,
    RANK_EMOJI,
    RANK_MEMBER_LINE,
    RANK_NAME,
    RANK_SET_DONE,
    RANK_SET_MENU,
    TRANSFER_CONFIRM,
    TRANSFER_DONE,
    TRANSFER_PROMPT,
)
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_ranks")


async def _render_ranks(session: AsyncSession, clan_id: int) -> tuple[str, InlineKeyboardMarkup]:
    clan = await clan_repo.get_by_id(session, clan_id)
    rows = await clan_service.list_members_with_users(session, clan_id)
    members = [
        (m.user_id, RANK_MEMBER_LINE.format(rank_emoji=RANK_EMOJI[m.rank.value], name=u.display_name))
        for m, u in rows
        if m.rank != ClanRank.owner
    ]
    text = RANKS_HEADER.format(name=clan.name if clan else "")
    return text, ranks_menu(members)


@router.callback_query(F.data == CB_CLAN_RANKS)
async def cb_ranks(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank != ClanRank.owner:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()
    text, keyboard = await _render_ranks(session, member.clan_id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_CLAN_SET_RANK_PREFIX))
async def cb_set_rank(callback: CallbackQuery, session: AsyncSession) -> None:
    rest = callback.data[len(CB_CLAN_SET_RANK_PREFIX) :]
    parts = rest.split(":", 1)
    target_user_id = int(parts[0])

    actor_id = callback.from_user.id
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.rank != ClanRank.owner:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return

    if len(parts) == 1:
        # Шаг 1: выбрали участника — показать выбор нового ранга.
        target = await clan_repo.get_member(session, target_user_id)
        if target is None or target.clan_id != member.clan_id or target.rank == ClanRank.owner:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        await callback.answer()
        target_user = await get_user_by_id(session, target_user_id)
        name = target_user.display_name if target_user else str(target_user_id)
        text = RANK_SET_MENU.format(name=name, rank_name=RANK_NAME[target.rank.value])
        await safe_edit_text(callback.message, text, reply_markup=rank_set_menu(target_user_id))
        return

    # Шаг 2: применить выбранный ранг.
    new_rank = ClanRank(parts[1])
    try:
        await clan_service.set_member_rank(
            session, clan_id=member.clan_id, actor_id=actor_id, target_user_id=target_user_id, new_rank=new_rank
        )
    except clan_service.NotAuthorizedError:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    except clan_service.NotInClanError:
        await callback.answer()
        return

    target_user = await get_user_by_id(session, target_user_id)
    name = target_user.display_name if target_user else str(target_user_id)
    await callback.answer(RANK_SET_DONE.format(name=name, rank_name=RANK_NAME[new_rank.value]), show_alert=True)

    text, keyboard = await _render_ranks(session, member.clan_id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data == CB_CLAN_TRANSFER_START)
async def cb_transfer_start(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank != ClanRank.owner:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()

    rows = await clan_service.list_members_with_users(session, member.clan_id)
    members = [(m.user_id, u.display_name) for m, u in rows if m.rank != ClanRank.owner]
    await safe_edit_text(callback.message, TRANSFER_PROMPT, reply_markup=transfer_menu(members))


@router.callback_query(F.data.startswith(CB_CLAN_TRANSFER_CONFIRM_PREFIX))
async def cb_transfer_confirm_step(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    rest = callback.data[len(CB_CLAN_TRANSFER_CONFIRM_PREFIX) :]
    parts = rest.split(":", 1)
    target_user_id = int(parts[0])
    actor_id = callback.from_user.id

    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.rank != ClanRank.owner:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return

    if len(parts) == 1:
        # Шаг 1: выбрали, кому передать — показать подтверждение.
        await callback.answer()
        target_user = await get_user_by_id(session, target_user_id)
        name = target_user.display_name if target_user else str(target_user_id)
        clan = await clan_repo.get_by_id(session, member.clan_id)
        text = TRANSFER_CONFIRM.format(clan_name=clan.name if clan else "", name=name)
        await safe_edit_text(callback.message, text, reply_markup=transfer_confirm_menu(target_user_id))
        return

    # Шаг 2 (parts[1] == "confirm"): применить передачу.
    async with try_acquire(redis, action_lock(actor_id, LOCK_ACTION_TRANSFER_OWNERSHIP)) as acquired:
        if not acquired:
            await callback.answer()
            return

        try:
            await clan_service.transfer_ownership(
                session, clan_id=member.clan_id, current_owner_id=actor_id, new_owner_id=target_user_id
            )
        except clan_service.NotAuthorizedError:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        except clan_service.NotInClanError:
            await callback.answer()
            return
        await callback.answer()

    target_user = await get_user_by_id(session, target_user_id)
    name = target_user.display_name if target_user else str(target_user_id)
    await callback.message.answer(TRANSFER_DONE.format(name=name))

    new_member = await clan_repo.get_member(session, actor_id)
    await render_clan_card(bot, callback.message.chat.id, session, new_member, old_message=callback.message)
