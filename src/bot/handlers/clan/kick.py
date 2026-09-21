from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import action_lock
from bot.cache.lock import try_acquire
from bot.constant.clan import CB_CLAN_KICK_CONFIRM_PREFIX, CB_CLAN_KICK_START, LOCK_ACTION_KICK_MEMBER
from bot.db.repositories import clan as clan_repo
from bot.db.repositories.user import get_by_id as get_user_by_id
from bot.handlers.clan.clan import render_clan_card
from bot.keyboards.clan import kick_confirm_menu, kick_menu
from bot.services import clan as clan_service
from bot.texts.clan import KICK_CONFIRM, KICK_DONE, KICK_EMPTY, KICK_NOT_ALLOWED, KICK_PROMPT, NOTIFY_KICKED, NOT_AUTHORIZED
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="clan_kick")


@router.callback_query(F.data == CB_CLAN_KICK_START)
async def cb_kick_start(callback: CallbackQuery, session: AsyncSession) -> None:
    actor = await clan_repo.get_member(session, callback.from_user.id)
    if actor is None or actor.rank not in clan_service.KICK_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return
    await callback.answer()

    rows = await clan_service.list_kickable_members(session, clan_id=actor.clan_id, actor_id=actor.user_id)
    candidates = [(m.user_id, u.display_name) for m, u in rows]
    text = KICK_PROMPT if candidates else KICK_EMPTY
    await safe_edit_text(callback.message, text, reply_markup=kick_menu(candidates))


@router.callback_query(F.data.startswith(CB_CLAN_KICK_CONFIRM_PREFIX))
async def cb_kick_confirm_step(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    rest = callback.data[len(CB_CLAN_KICK_CONFIRM_PREFIX) :]
    parts = rest.split(":", 1)
    target_user_id = int(parts[0])
    actor_id = callback.from_user.id

    actor = await clan_repo.get_member(session, actor_id)
    if actor is None or actor.rank not in clan_service.KICK_RANKS:
        await callback.answer(NOT_AUTHORIZED, show_alert=True)
        return

    if len(parts) == 1:
        # Шаг 1: выбрали, кого кикнуть — показать подтверждение.
        await callback.answer()
        target_user = await get_user_by_id(session, target_user_id)
        name = target_user.display_name if target_user else str(target_user_id)
        await safe_edit_text(callback.message, KICK_CONFIRM.format(name=name), reply_markup=kick_confirm_menu(target_user_id))
        return

    # Шаг 2 (parts[1] == "confirm"): применить кик.
    async with try_acquire(redis, action_lock(actor_id, LOCK_ACTION_KICK_MEMBER)) as acquired:
        if not acquired:
            await callback.answer()
            return

        clan_name = await clan_repo.get_name(session, actor.clan_id)
        try:
            await clan_service.kick_member(session, clan_id=actor.clan_id, actor_id=actor_id, target_user_id=target_user_id)
        except clan_service.NotAuthorizedError:
            await callback.answer(NOT_AUTHORIZED, show_alert=True)
            return
        except clan_service.NotInClanError:
            await callback.answer()
            return
        except clan_service.CannotKickHigherRankError:
            await callback.answer(KICK_NOT_ALLOWED, show_alert=True)
            return

    target_user = await get_user_by_id(session, target_user_id)
    name = target_user.display_name if target_user else str(target_user_id)
    await callback.answer(KICK_DONE.format(name=name), show_alert=True)
    await notify(bot, target_user_id, NOTIFY_KICKED.format(name=clan_name or ""))

    new_member = await clan_repo.get_member(session, actor_id)
    await render_clan_card(bot, callback.message.chat.id, session, new_member, old_message=callback.message)
