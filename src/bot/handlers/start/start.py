from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.user import upsert_from_telegram
from bot.keyboards.common import main_menu
from bot.services import referral as referral_service
from bot.texts.common import WELCOME

router = Router(name="start")

_REFERRAL_PAYLOAD_PREFIX = "ref_"


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, session: AsyncSession) -> None:
    display_name = message.from_user.full_name[:32]
    await upsert_from_telegram(
        session,
        user_id=message.from_user.id,
        username=message.from_user.username,
        display_name=display_name,
    )

    # Именная реф. кампания из /admin (t.me/<bot>?start=ref_<код>) — не путать с личными
    # реф. ссылками игроков (см. TODO.md, план в профиле, ещё не спроектирован). Неизвестный
    # код молча игнорируется — битая/устаревшая ссылка не должна ломать /start.
    if command.args and command.args.startswith(_REFERRAL_PAYLOAD_PREFIX):
        code = command.args[len(_REFERRAL_PAYLOAD_PREFIX) :]
        await referral_service.record_visit(session, code=code, user_id=message.from_user.id)

    await message.answer(WELCOME, reply_markup=main_menu())
