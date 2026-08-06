from __future__ import annotations

from typing import Any

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InputMedia, Message


async def safe_edit_text(message: Message, text: str, **kwargs: Any) -> None:
    """edit_text, который проглатывает "message is not modified" — неизбежный побочный
    эффект защиты от повторных кликов (см. CLAUDE.md, правило 2): пока обрабатывался
    первый клик, второй уже мог прилететь и отредактировать то же самое.

    Также подстраховывает от правила 12 (CLAUDE.md): если экран открыли поверх сообщения
    без текста (фото с подписью — например, карточка клана с картинкой, см.
    handlers/clan/clan.py: _send_card), Telegram не даёт editMessageText его сконвертировать.
    В этом случае — как и в _send_card — удаляем и присылаем текстовое сообщение заново,
    вместо того чтобы падать. Без этого падают ВСЕ под-экраны клана (участники, заявки,
    ранги, редактирование, обмен, война, топ), как только у клана появляется картинка —
    они все вызывают именно эту функцию на callback.message."""
    try:
        await message.edit_text(text, **kwargs)
    except TelegramBadRequest as exc:
        err = str(exc).lower()
        if "message is not modified" in err:
            return
        if "there is no text in the message to edit" in err:
            try:
                await message.delete()
            except TelegramBadRequest:
                pass
            await message.answer(text, **kwargs)
            return
        raise


async def safe_edit_media(message: Message, media: InputMedia, **kwargs: Any) -> Message | None:
    """Аналог safe_edit_text для сообщений с фото (навигация по коллекции) — меняет и
    картинку, и подпись атомарно одним вызовом Telegram API, вместо спама новыми
    сообщениями на каждый клик -1/+1. Возвращает отредактированное сообщение (нужно
    вызывающему коду, чтобы закэшировать новый file_id, см. utils/card_media) — либо
    None, если Telegram счёл, что менять нечего (тогда file_id уже актуален в кэше)."""
    try:
        return await message.edit_media(media, **kwargs)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc).lower():
            raise
        return None
