from __future__ import annotations

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError


async def notify(bot: Bot, user_id: int, text: str) -> None:
    """Проактивное уведомление в личку. Молча игнорируем ошибку доставки — получатель мог
    заблокировать бота или удалить аккаунт, это не повод падать посреди чужого действия
    (заявка/приглашение/перевод пыли/фоновый шедулер всё равно уже применили эффект)."""
    try:
        await bot.send_message(user_id, text)
    except TelegramAPIError:
        pass
