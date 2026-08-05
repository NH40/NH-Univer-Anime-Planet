from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from bot.db.models.season import Season


async def get_active(session: AsyncSession) -> Season | None:
    result = await session.execute(select(Season).where(Season.is_active.is_(True)).limit(1))
    return result.scalar_one_or_none()


async def create(session: AsyncSession, *, version: str) -> Season:
    """Не коммитит — часть составной операции start_new_season (см. services/season):
    старый сезон обязан быть уже завершён (end_active) в той же транзакции ДО этого
    вызова — иначе временно нарушится partial unique index (максимум один активный)."""
    season = Season(version=version, is_active=True)
    session.add(season)
    await session.flush()
    return season


async def end_active(session: AsyncSession, *, season_id: int) -> None:
    await session.execute(
        update(Season).where(Season.id == season_id).values(is_active=False, ended_at=func.now())
    )


async def set_version(session: AsyncSession, *, season_id: int, version: str) -> None:
    await session.execute(update(Season).where(Season.id == season_id).values(version=version))
