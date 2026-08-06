from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import wipe_confirm_flag
from bot.config.settings import get_settings
from bot.constant.admin import CB_ADMIN_WIPE_CONFIRM, CB_ADMIN_WIPE_START
from bot.keyboards.admin import wipe_confirm_menu
from bot.services import admin as admin_service
from bot.texts.admin import NOT_SUPER_ADMIN, WIPE_CONFIRM_EXPIRED, WIPE_CONFIRM_PROMPT, WIPE_DONE, WIPE_DONE_BROADCAST
from bot.utils.notify import notify
from bot.utils.safe_edit import safe_edit_text

router = Router(name="admin_db_wipe")

# Окно между первым и вторым нажатием — защита от случайного повтора спустя время, не от
# спам-клика (тот уже ловит общий ThrottlingMiddleware).
_WIPE_CONFIRM_TTL_SECONDS = 30


@router.callback_query(F.data == CB_ADMIN_WIPE_START)
async def cb_wipe_start(callback: CallbackQuery, redis: Redis) -> None:
    settings = get_settings()
    if not admin_service.is_config_admin(callback.from_user.id, settings):
        await callback.answer(NOT_SUPER_ADMIN, show_alert=True)
        return

    await redis.set(wipe_confirm_flag(callback.from_user.id), "1", ex=_WIPE_CONFIRM_TTL_SECONDS)
    await callback.answer()
    await safe_edit_text(callback.message, WIPE_CONFIRM_PROMPT, reply_markup=wipe_confirm_menu())


@router.callback_query(F.data == CB_ADMIN_WIPE_CONFIRM)
async def cb_wipe_confirm(callback: CallbackQuery, session: AsyncSession, redis: Redis, bot: Bot) -> None:
    settings = get_settings()
    if not admin_service.is_config_admin(callback.from_user.id, settings):
        await callback.answer(NOT_SUPER_ADMIN, show_alert=True)
        return

    # Второе нажатие валидно только пока жив флаг первого — не просто "два разных callback
    # подряд", иначе подтверждение, забытое на часы, сработало бы случайно спустя время.
    confirmed = await redis.delete(wipe_confirm_flag(callback.from_user.id))
    if not confirmed:
        await callback.answer(WIPE_CONFIRM_EXPIRED, show_alert=True)
        return

    await admin_service.wipe_database(session)
    await callback.answer(WIPE_DONE, show_alert=True)
    await safe_edit_text(callback.message, WIPE_DONE, reply_markup=InlineKeyboardMarkup(inline_keyboard=[]))

    admin_name = callback.from_user.username or str(callback.from_user.id)
    for admin_id in settings.admin_ids:
        await notify(bot, admin_id, WIPE_DONE_BROADCAST.format(name=admin_name))
