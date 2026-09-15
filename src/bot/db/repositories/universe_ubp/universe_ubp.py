from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.user_universe_ubp import UserUniverseUbp


async def award(session: AsyncSession, *, user_id: int, universe_code: str, amount: int) -> int:
    """Апсерт по (user_id, universe_code): новая строка с ubp_season=amount, либо
    ubp_season += amount если строка уже есть. `amount` может быть отрицательным (симметрично
    award_ubp — см. services/ubp). Возвращает итоговый ubp_season, тем же RETURNING, без
    отдельного SELECT (нужно для синхронизации Redis-лидерборда вселенной). Не коммитит —
    часть составной операции (крутка/слияние), коммитит вызывающий сервис верхнего уровня."""
    stmt = (
        pg_insert(UserUniverseUbp)
        .values(user_id=user_id, universe_code=universe_code, ubp_season=amount)
        .on_conflict_do_update(
            index_elements=[UserUniverseUbp.user_id, UserUniverseUbp.universe_code],
            set_={"ubp_season": UserUniverseUbp.ubp_season + amount},
        )
        .returning(UserUniverseUbp.ubp_season)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_rank_row(session: AsyncSession, *, user_id: int, universe_code: str) -> UserUniverseUbp | None:
    return await session.get(UserUniverseUbp, {"user_id": user_id, "universe_code": universe_code})


@dataclass
class UniverseTopRow:
    user_id: int
    ubp: int


async def get_top_from_db(
    session: AsyncSession, *, universe_code: str, by_total: bool, limit: int | None = None
) -> list[UniverseTopRow]:
    """Читает топ прямо из Postgres (источник правды) — используется только для
    "за всё время" (нет отдельного Redis-лидерборда для ubp_total, см. CLAUDE.md: тот не
    меняется вне смены сезона, а /top "за все время" — чисто информационный экран без
    награды) и для холодного restore Redis-лидерборда "за сезон" (см.
    cache/universe_leaderboard.rebuild_if_missing, `limit=None` — забрать все строки)."""
    column = UserUniverseUbp.ubp_total if by_total else UserUniverseUbp.ubp_season
    stmt = (
        select(UserUniverseUbp.user_id, column)
        .where(UserUniverseUbp.universe_code == universe_code, column > 0)
        .order_by(column.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return [UniverseTopRow(user_id=uid, ubp=ubp) for uid, ubp in result.all()]


async def list_season_rows_for_reset(session: AsyncSession, *, universe_code: str, limit: int) -> list[UniverseTopRow]:
    return await get_top_from_db(session, universe_code=universe_code, by_total=False, limit=limit)


async def transfer_season_to_total(session: AsyncSession) -> None:
    """Смена сезона (см. services/season.start_new_season) — тот же перенос, что у
    User.ubp_season -> ubp_total, но по ВСЕМ строкам user_universe_ubp разом одним UPDATE
    без WHERE (правило 3 — никакого Python-цикла по игрокам/вселенным)."""
    await session.execute(update(UserUniverseUbp).values(ubp_total=UserUniverseUbp.ubp_total + UserUniverseUbp.ubp_season, ubp_season=0))
