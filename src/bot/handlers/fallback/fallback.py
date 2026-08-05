from __future__ import annotations

from aiogram import Router
from aiogram.types import CallbackQuery, Message

from bot.texts.common import UNKNOWN_CALLBACK, UNKNOWN_MESSAGE

router = Router(name="fallback")


@router.message()
async def unknown_message(message: Message) -> None:
    """Единый catch-all — регистрируется САМЫМ ПОСЛЕДНИМ в get_routers() (см.
    handlers/__init__.py), поэтому срабатывает только если ни один другой роутер (в т.ч.
    FSM-хендлеры по состояниям, у каждого своя валидация "не то прислали") апдейт не забрал."""
    await message.answer(UNKNOWN_MESSAGE)


@router.callback_query()
async def unknown_callback(callback: CallbackQuery) -> None:
    await callback.answer(UNKNOWN_CALLBACK, show_alert=True)
