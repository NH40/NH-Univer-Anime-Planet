from __future__ import annotations

import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories.user import list_all_ids

# Telegram допускает ~30 сообщений/сек в разные чаты — шлём чанками с паузой, с запасом
# по лимиту (см. CLAUDE.md, "Рассылка"). Не игровой баланс (правило 8 про config/game —
# это про шансы/лимиты/формулы), инженерный параметр конкретно этого таска.
BROADCAST_CHUNK_SIZE = 25
BROADCAST_CHUNK_DELAY_SECONDS = 1.0


async def _send_one(bot: Bot, user_id: int, text: str) -> bool:
    try:
        await bot.send_message(user_id, text)
        return True
    except TelegramAPIError:
        return False


async def run_broadcast(bot: Bot, session: AsyncSession, text: str) -> tuple[int, int]:
    """Рассылает `text` всем игрокам батчами, не блокируя остальной бот (вызывается из
    фонового asyncio-таска, см. handlers/admin/broadcast.py — не await прямо в хендлере,
    иначе на 30k игроков обработка апдейта растянется на минуты). Возвращает
    (доставлено, не доставлено) — недоставленные, как правило, заблокировали бота."""
    user_ids = await list_all_ids(session)
    sent = 0
    failed = 0

    for i in range(0, len(user_ids), BROADCAST_CHUNK_SIZE):
        chunk = user_ids[i : i + BROADCAST_CHUNK_SIZE]
        results = await asyncio.gather(*(_send_one(bot, user_id, text) for user_id in chunk))
        sent += sum(results)
        failed += len(results) - sum(results)
        await asyncio.sleep(BROADCAST_CHUNK_DELAY_SECONDS)

    return sent, failed
