from __future__ import annotations

from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMedia, Message


async def safe_edit_text(message: Message, text: str, **kwargs: Any) -> None:
    """edit_text, который проглатывает "message is not modified" — неизбежный побочный
    эффект защиты от повторных кликов (см. CLAUDE.md, правило 2): пока обрабатывался
    первый клик, второй уже мог прилететь и отредактировать то же самое."""
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise


async def safe_edit_media(message: Message, media: InputMedia, **kwargs: Any) -> None:
    """Аналог safe_edit_text для сообщений с фото (навигация по коллекции) — меняет и
    картинку, и подпись атомарно одним вызовом Telegram API, вместо спама новыми
    сообщениями на каждый клик -1/+1."""
    try:
        await message.edit_media(media, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
