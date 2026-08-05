from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.clan import (
    CB_CLAN_ACCEPT_INVITE_PREFIX,
    CB_CLAN_ACCEPT_PREFIX,
    CB_CLAN_DECLINE_INVITE_PREFIX,
    CB_CLAN_INVITE_START,
    CB_CLAN_MY_INVITES,
    CB_CLAN_REJECT_PREFIX,
    CB_CLAN_REQUESTS,
    LOCK_ACTION_ACCEPT_APPLICATION,
)
from bot.db.models.clan import MAX_CLAN_MEMBERS
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.db.repositories.user import get_by_username as get_user_by_username
from bot.db.repositories.user import get_many_by_ids
from bot.handlers.clan.clan import render_clan_card
from bot.keyboards.clan import my_invites_menu, requests_menu
from bot.services import clan as clan_service
from bot.states.clan import ClanStates
from bot.texts.clan import (
    ACTION_CANCELLED,
    CLAN_FULL,
    CREATE_CLAN_ALREADY_IN_CLAN,
    INVITE_ACCEPTED,
    INVITE_ALREADY_IN_CLAN,
    INVITE_DECLINED,
    INVITE_PROMPT,
    INVITE_SENT,
    INVITE_USER_NOT_FOUND,
    MY_INVITES_EMPTY,
    MY_INVITES_HEADER,
    NOTIFY_INVITE_RECEIVED,
    NOTIFY_NEW_APPLICATION,
    NOT_AUTHORIZED,
    REQUESTS_EMPTY,
    REQUESTS_HEADER,
    REQUEST_ACCEPTED,
    REQUEST_LINE,
    REQUEST_REJECTED,
)
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_requests")


async def _render_requests(session: AsyncSession, clan_id: int) -> tuple[str, InlineKeyboardMarkup]:
    requests = await clan_service.list_applications(session, clan_id)
    if not requests:
        return REQUESTS_HEADER + REQUESTS_EMPTY, requests_menu([])

    users = await get_many_by_ids(session, [r.user_id for r in requests])
    rows = [(r.user_id, users[r.user_id].username or str(r.user_id)) for r in requests if r.user_id in users]
    lines = "".join(REQUEST_LINE.format(username=username) + "\n" for _uid, username in rows)
    return REQUESTS_HEADER + lines, requests_menu(rows)


async def _render_my_invites(session: AsyncSession, user_id: int) -> tuple[str, InlineKeyboardMarkup]:
    invites = await clan_repo.list_invites_for_user(session, user_id)
    if not invites:
        return MY_INVITES_HEADER + MY_INVITES_EMPTY, my_invites_menu([])

    clans = await clan_repo.get_many_by_ids(session, [r.clan_id for r in invites])
    rows = [(r.clan_id, clans[r.clan_id].name) for r in invites if r.clan_id in clans]
    return MY_INVITES_HEADER, my_invites_menu(rows)


# --- Заявки (владелец/зам клана рассматривает входящие заявки игроков) ---


@router.callback_query(F.data == CB_CLAN_REQUESTS)
async def cb_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()
    text, keyboard = await _render_requests(session, member.clan_id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_CLAN_ACCEPT_PREFIX))
async def cb_accept_application(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    target_user_id = int(callback.data[len(CB_CLAN_ACCEPT_PREFIX) :])
    actor_id = callback.from_user.id
    async with try_acquire(redis, action_lock(actor_id, LOCK_ACTION_ACCEPT_APPLICATION)) as acquired:
        if not acquired:
            await callback.answer()
            return

        member = await clan_repo.get_member(session, actor_id)
        if member is None:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        clan_id = member.clan_id

        try:
            await clan_service.accept_application(session, clan_id=clan_id, user_id=target_user_id, actor_id=actor_id)
        except clan_service.NotAuthorizedError:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        except clan_service.RequestNotFoundError:
            await callback.answer()
            return
        except clan_service.ClanFullError:
            await callback.answer(CLAN_FULL.format(max=MAX_CLAN_MEMBERS), show_alert=True)
            return
        except clan_service.AlreadyInClanError:
            await callback.answer()
            return
        await callback.answer()

    target_user = await get_user_by_id(session, target_user_id)
    username = target_user.username if target_user and target_user.username else str(target_user_id)
    await callback.message.answer(REQUEST_ACCEPTED.format(username=username))

    text, keyboard = await _render_requests(session, clan_id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)

    if target_user is not None and target_user.notifications_enabled:
        clan = await clan_repo.get_by_id(session, clan_id)
        await notify(bot, target_user_id, INVITE_ACCEPTED.format(clan_name=clan.name if clan else ""))


@router.callback_query(F.data.startswith(CB_CLAN_REJECT_PREFIX))
async def cb_reject_application(callback: CallbackQuery, session: AsyncSession) -> None:
    target_user_id = int(callback.data[len(CB_CLAN_REJECT_PREFIX) :])
    actor_id = callback.from_user.id
    member = await clan_repo.get_member(session, actor_id)
    if member is None:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    clan_id = member.clan_id

    try:
        await clan_service.reject_application(session, clan_id=clan_id, user_id=target_user_id, actor_id=actor_id)
    except clan_service.NotAuthorizedError:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()

    target_user = await get_user_by_id(session, target_user_id)
    username = target_user.username if target_user and target_user.username else str(target_user_id)
    await callback.message.answer(REQUEST_REJECTED.format(username=username))

    text, keyboard = await _render_requests(session, clan_id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


# --- Приглашение игрока (владелец/зам зовёт конкретного игрока по username) ---


@router.callback_query(F.data == CB_CLAN_INVITE_START)
async def cb_invite_start(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    member = await clan_repo.get_member(session, callback.from_user.id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await state.set_state(ClanStates.waiting_invite_username)
    await callback.answer()
    await safe_edit_text(callback.message, INVITE_PROMPT, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))


@router.message(StateFilter(ClanStates.waiting_invite_username), Command("cancel"))
async def cancel_invite(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(ACTION_CANCELLED)


@router.message(StateFilter(ClanStates.waiting_invite_username))
async def apply_invite(message: Message, state: FSMContext, session: AsyncSession, bot: Bot) -> None:
    raw = (message.text or "").strip().lstrip("@")
    await state.clear()

    actor_id = message.from_user.id
    member = await clan_repo.get_member(session, actor_id)
    if member is None or member.rank not in clan_service.MANAGER_RANKS:
        await message.answer(NOT_AUTHORIZED)
        return

    target = await get_user_by_username(session, raw)
    if target is None:
        await message.answer(INVITE_USER_NOT_FOUND)
        return

    try:
        await clan_service.invite_player(session, clan_id=member.clan_id, target_user_id=target.id, actor_id=actor_id)
    except clan_service.NotAuthorizedError:
        await message.answer(NOT_AUTHORIZED)
        return
    except clan_service.AlreadyInClanError:
        await message.answer(INVITE_ALREADY_IN_CLAN)
        return

    username = target.username or str(target.id)
    await message.answer(INVITE_SENT.format(username=username))
    if target.notify_clan_requests:
        clan = await clan_repo.get_by_id(session, member.clan_id)
        await notify(bot, target.id, NOTIFY_INVITE_RECEIVED.format(clan_name=clan.name if clan else ""))


# --- Мои приглашения (сам игрок принимает/отклоняет входящие приглашения кланов) ---


@router.callback_query(F.data == CB_CLAN_MY_INVITES)
async def cb_my_invites(callback: CallbackQuery, session: AsyncSession) -> None:
    await callback.answer()
    text, keyboard = await _render_my_invites(session, callback.from_user.id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)


@router.callback_query(F.data.startswith(CB_CLAN_ACCEPT_INVITE_PREFIX))
async def cb_accept_invite(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    clan_id = int(callback.data[len(CB_CLAN_ACCEPT_INVITE_PREFIX) :])
    user_id = callback.from_user.id

    try:
        await clan_service.accept_invite(session, clan_id=clan_id, user_id=user_id)
    except clan_service.RequestNotFoundError:
        await callback.answer()
        return
    except clan_service.ClanFullError:
        await callback.answer(CLAN_FULL.format(max=MAX_CLAN_MEMBERS), show_alert=True)
        return
    except clan_service.AlreadyInClanError:
        await callback.answer(CREATE_CLAN_ALREADY_IN_CLAN, show_alert=True)
        return

    clan = await clan_repo.get_by_id(session, clan_id)
    await callback.answer(INVITE_ACCEPTED.format(clan_name=clan.name if clan else ""), show_alert=True)

    member = await clan_repo.get_member(session, user_id)
    await render_clan_card(bot, callback.message.chat.id, session, member, old_message=callback.message)


@router.callback_query(F.data.startswith(CB_CLAN_DECLINE_INVITE_PREFIX))
async def cb_decline_invite(callback: CallbackQuery, session: AsyncSession) -> None:
    clan_id = int(callback.data[len(CB_CLAN_DECLINE_INVITE_PREFIX) :])
    await clan_service.decline_invite(session, clan_id=clan_id, user_id=callback.from_user.id)
    await callback.answer(INVITE_DECLINED, show_alert=True)

    text, keyboard = await _render_my_invites(session, callback.from_user.id)
    await safe_edit_text(callback.message, text, reply_markup=keyboard)
