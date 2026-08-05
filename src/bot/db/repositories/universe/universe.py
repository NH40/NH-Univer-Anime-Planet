from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.universe import Universe


async def list_active(session: AsyncSession) -> list[Universe]:
    result = await session.execute(
        select(Universe).where(Universe.is_active.is_(True)).order_by(Universe.title)
    )
    return list(result.scalars().all())


async def get_by_code(session: AsyncSession, code: str) -> Universe | None:
    return await session.get(Universe, code)
