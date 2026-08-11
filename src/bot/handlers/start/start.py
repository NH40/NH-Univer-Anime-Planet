from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import TICKET_STARTING_COUNT
from bot.constant.referral import REFERRAL_DEEPLINK_PREFIX
from bot.db.repositories.user import get_by_id, set_referred_by, upsert_from_telegram
from bot.handlers.profile.profile import show_profile
from bot.keyboards.common import main_menu
from bot.services import referral as referral_service
from bot.texts.common import WELCOME

router = Router(name="start")

_REFERRAL_PAYLOAD_PREFIX = "ref_"


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession, redis: Redis) -> None:
    user_id = message.from_user.id
    display_name = message.from_user.full_name[:32]
    # Не первый /start (игрок уже был зарегистрирован) — открываем профиль вместо
    # приветственного сообщения (запрос пользователя 2026-08-11): реф-ссылки/deep-link'и
    # всё равно нужно обработать один раз, а не только новым игрокам.
    is_returning = await get_by_id(session, user_id) is not None
    await upsert_from_telegram(
        session,
        user_id=user_id,
        username=message.from_user.username,
        display_name=display_name,
        starting_tickets=TICKET_STARTING_COUNT,
    )

    # Именная реф. кампания из /admin (t.me/<bot>?start=ref_<код>) — не путать с личными
    # реф. ссылками игроков ниже. Неизвестный код молча игнорируется — битая/устаревшая
    # ссылка не должна ломать /start.
    if command.args and command.args.startswith(_REFERRAL_PAYLOAD_PREFIX):
        code = command.args[len(_REFERRAL_PAYLOAD_PREFIX) :]
        await referral_service.record_visit(session, code=code, user_id=user_id)
    # Личная реф. ссылка игрока (t.me/<bot>?start=r_<user_id>, см. CLAUDE.md, "Рефералы") —
    # referred_by_id ставится один раз (set_referred_by — WHERE ... IS NULL, повторные заходы
    # по ссылке ничего не портят). Реферер обязан существовать (FK) — иначе просто игнорируем,
    # как и битый ref_-код; нельзя указать себя же (переход по собственной ссылке).
    elif command.args and command.args.startswith(REFERRAL_DEEPLINK_PREFIX):
        raw_referrer_id = command.args[len(REFERRAL_DEEPLINK_PREFIX) :]
        if raw_referrer_id.isdigit():
            referrer_id = int(raw_referrer_id)
            if referrer_id != user_id and await get_by_id(session, referrer_id) is not None:
                await set_referred_by(session, user_id=user_id, referrer_id=referrer_id)

    if is_returning:
        await show_profile(message, session, redis)
        return
    await message.answer(WELCOME, reply_markup=main_menu())
