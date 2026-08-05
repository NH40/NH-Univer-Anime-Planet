from __future__ import annotations

import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis

_RELEASE_SCRIPT = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


@asynccontextmanager
async def try_acquire(redis: Redis, key: str, ttl_ms: int = 3000) -> AsyncIterator[bool]:
    """Неблокирующий лок для защиты от повторного клика по одной и той же кнопке.
    Использование:

        async with try_acquire(redis, keys.action_lock(user_id, "roll_1")) as acquired:
            if not acquired:
                return  # уже обрабатывается — молча игнорируем повторный клик
            ...

    Лок снимается только тем, кто его поставил (проверка токена), чтобы не погасить
    чужой лок при протухании по TTL.
    """
    token = secrets.token_hex(8)
    acquired = await redis.set(key, token, nx=True, px=ttl_ms)
    try:
        yield bool(acquired)
    finally:
        if acquired:
            await redis.eval(_RELEASE_SCRIPT, 1, key, token)
