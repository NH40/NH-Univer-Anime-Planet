from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.universe import Universe


async def list_active(session: AsyncSession) -> list[Universe]:
    """Активные НЕ-ивентовые вселенные — то, что игрок может выбрать для крутки в
    Настройках (см. CLAUDE.md, "Ивенты"). Ивентовые вселенные недоступны для ручного
    выбора — их карты попадают в инвентарь только через отдельный шанс в самой крутке."""
    result = await session.execute(
        select(Universe)
        .where(Universe.is_active.is_(True), Universe.is_event.is_(False))
        .order_by(Universe.title)
    )
    return list(result.scalars().all())


async def get_by_code(session: AsyncSession, code: str) -> Universe | None:
    return await session.get(Universe, code)
