from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import leaderboard_players_season
from bot.db.models.user import User

# Redis — не источник правды (см. CLAUDE.md, правило 4): если ключ отсутствует
# (холодный старт/после рестарта Redis без персистентности), пересобираем из Postgres.


async def sync_score(redis: Redis, season_id: int, user_id: int, ubp_season: int) -> None:
    await redis.zadd(leaderboard_players_season(season_id), {str(user_id): ubp_season})


async def rebuild_if_missing(redis: Redis, session: AsyncSession, season_id: int) -> None:
    key = leaderboard_players_season(season_id)
    if await redis.exists(key):
        return

    result = await session.execute(
        select(User.id, User.ubp_season).where(User.ubp_season > 0)
    )
    rows = result.all()
    if not rows:
        return

    pipe = redis.pipeline(transaction=False)
    for user_id, ubp_season in rows:
        pipe.zadd(key, {str(user_id): ubp_season})
    await pipe.execute()


async def get_top(redis: Redis, session: AsyncSession, season_id: int, count: int) -> list[tuple[int, int]]:
    await rebuild_if_missing(redis, session, season_id)
    raw = await redis.zrevrange(leaderboard_players_season(season_id), 0, count - 1, withscores=True)
    return [(int(user_id), int(score)) for user_id, score in raw]


async def get_page(
    redis: Redis, session: AsyncSession, season_id: int, start: int, end: int
) -> list[tuple[int, int]]:
    """start/end — индексы ранга (0-based, включительно), результат отсортирован по убыванию UBP."""
    await rebuild_if_missing(redis, session, season_id)
    raw = await redis.zrevrange(leaderboard_players_season(season_id), start, end, withscores=True)
    return [(int(user_id), int(score)) for user_id, score in raw]


async def get_count(redis: Redis, session: AsyncSession, season_id: int) -> int:
    await rebuild_if_missing(redis, session, season_id)
    return await redis.zcard(leaderboard_players_season(season_id))


async def get_rank(redis: Redis, season_id: int, user_id: int) -> int | None:
    """Возвращает место в топе (1-based) или None, если игрока ещё нет в рейтинге (ubp_season=0)."""
    rank = await redis.zrevrank(leaderboard_players_season(season_id), str(user_id))
    return None if rank is None else rank + 1
