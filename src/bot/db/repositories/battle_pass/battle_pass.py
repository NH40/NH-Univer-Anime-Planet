from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.battle_pass import BattlePass


async def get(session: AsyncSession, *, user_id: int, season_id: int) -> BattlePass | None:
    return await session.get(BattlePass, (user_id, season_id))


async def get_or_create(session: AsyncSession, *, user_id: int, season_id: int) -> BattlePass:
    """Первое открытие экрана пасса в сезоне создаёт строку прогресса. Атомарный insert
    (ON CONFLICT DO NOTHING) — если гонка (два одновременных открытия), просто перечитываем
    то, что вставил конкурент. Коммитит — читающий вызов, не часть составной операции."""
    row = await get(session, user_id=user_id, season_id=season_id)
    if row is not None:
        return row

    stmt = (
        pg_insert(BattlePass)
        .values(user_id=user_id, season_id=season_id)
        .on_conflict_do_nothing(index_elements=[BattlePass.user_id, BattlePass.season_id])
        .returning(BattlePass)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        row = await get(session, user_id=user_id, season_id=season_id)
    await session.commit()
    return row


async def set_premium(session: AsyncSession, *, user_id: int, season_id: int) -> None:
    """Разово открывает премиум-ветку СЕЗОНА навсегда (см. docstring модели). Не коммитит —
    вызывается внутри services/shop.buy_premium_pass как часть той же транзакции покупки."""
    stmt = (
        pg_insert(BattlePass)
        .values(user_id=user_id, season_id=season_id, is_premium=True)
        .on_conflict_do_update(
            index_elements=[BattlePass.user_id, BattlePass.season_id],
            set_={"is_premium": True},
        )
    )
    await session.execute(stmt)


async def set_claimed_free_level(session: AsyncSession, *, user_id: int, season_id: int, level: int) -> None:
    """Не коммитит — часть составной операции claim_free (см. services/battle_pass)."""
    await session.execute(
        update(BattlePass)
        .where(BattlePass.user_id == user_id, BattlePass.season_id == season_id)
        .values(claimed_free_level=level)
    )


async def set_claimed_premium_level(session: AsyncSession, *, user_id: int, season_id: int, level: int) -> None:
    await session.execute(
        update(BattlePass)
        .where(BattlePass.user_id == user_id, BattlePass.season_id == season_id)
        .values(claimed_premium_level=level)
    )
