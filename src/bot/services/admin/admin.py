from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import tech_mode_flag
from bot.config.settings import Settings
from bot.db.repositories.user import get_by_id


def is_config_admin(user_id: int, settings: Settings) -> bool:
    """Супер-админы из `ADMIN_IDS` (.env) — единственные, кого не блокирует техрежим
    (см. CLAUDE.md, "Админ-панель"). Чистая проверка множества, без похода в БД."""
    return user_id in settings.admin_ids


async def is_admin(session: AsyncSession, user_id: int, settings: Settings) -> bool:
    """Полная проверка доступа к /admin — супер-админ из конфига ИЛИ доп. админ через БД
    (`User.is_admin`). Короткое замыкание на конфиге экономит запрос для супер-админов."""
    if is_config_admin(user_id, settings):
        return True
    user = await get_by_id(session, user_id)
    return user is not None and user.is_admin


async def get_tech_mode(redis: Redis) -> bool:
    return bool(await redis.get(tech_mode_flag()))


async def set_tech_mode(redis: Redis, enabled: bool) -> None:
    if enabled:
        await redis.set(tech_mode_flag(), "1")
    else:
        await redis.delete(tech_mode_flag())
