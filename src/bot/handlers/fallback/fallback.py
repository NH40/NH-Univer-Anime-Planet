from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from bot.keyboards.common import main_menu
from bot.texts.common import UNKNOWN_CALLBACK, UNKNOWN_MESSAGE

router = Router(name="fallback")


@router.message(F.chat.type == "private")
async def unknown_message(message: Message) -> None:
    """Единый catch-all — регистрируется САМЫМ ПОСЛЕДНИМ в get_routers() (см.
    handlers/__init__.py), поэтому срабатывает только если ни один другой роутер (в т.ч.
    FSM-хендлеры по состояниям, у каждого своя валидация "не то прислали") апдейт не забрал.
    Сразу прикладываем главное меню (не просим написать /start заново, см. запрос
    пользователя 2026-08-06) — игрок уже зарегистрирован, если дошёл до этого хендлера.
    Ограничено личными чатами (2026-08-15) — в группе бот получает поток обычной болтовни
    игроков, не адресованной ему; без фильтра catch-all отвечал "Не понял" на КАЖДОЕ такое
    сообщение, что и было жалобой пользователя."""
    await message.answer(UNKNOWN_MESSAGE, reply_markup=main_menu())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer(UNKNOWN_CALLBACK, show_alert=True)
