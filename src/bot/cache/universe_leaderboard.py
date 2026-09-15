from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.keys import leaderboard_universe_season
from bot.db.repositories import universe_ubp as universe_ubp_repo

# Тот же паттерн, что cache/leaderboard.py (лидерборд по общему UBP сезона), но по одной
# (сезон, вселенная) — см. CLAUDE.md, "Топ по вселенной". Redis — не источник правды
# (правило 4): при промахе (холодный старт/рестарт Redis без персистентности)
# пересобираем из Postgres (UserUniverseUbp.ubp_season).


async def sync_score(redis: Redis, season_id: int, universe_code: str, user_id: int, ubp_season: int) -> None:
    await redis.zadd(leaderboard_universe_season(season_id, universe_code), {str(user_id): ubp_season})


async def rebuild_if_missing(redis: Redis, session: AsyncSession, season_id: int, universe_code: str) -> None:
    key = leaderboard_universe_season(season_id, universe_code)
    if await redis.exists(key):
        return

    rows = await universe_ubp_repo.get_top_from_db(session, universe_code=universe_code, by_total=False)
    if not rows:
        return

    pipe = redis.pipeline(transaction=False)
    for row in rows:
        pipe.zadd(key, {str(row.user_id): row.ubp})
    await pipe.execute()


async def get_top(
    redis: Redis, session: AsyncSession, season_id: int, universe_code: str, count: int
) -> list[tuple[int, int]]:
    await rebuild_if_missing(redis, session, season_id, universe_code)
    raw = await redis.zrevrange(leaderboard_universe_season(season_id, universe_code), 0, count - 1, withscores=True)
    return [(int(user_id), int(score)) for user_id, score in raw]


async def get_rank(redis: Redis, season_id: int, universe_code: str, user_id: int) -> int | None:
    """Место в топе вселенной (1-based) или None, если игрок ещё не набрал UBP в ней в
    этом сезоне."""
    rank = await redis.zrevrank(leaderboard_universe_season(season_id, universe_code), str(user_id))
    return None if rank is None else rank + 1
