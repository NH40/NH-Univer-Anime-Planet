from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.battle_pass import TRACK_FREE
from bot.db.models.battle_pass import BattlePass
from bot.db.models.battle_pass_claim import BattlePassClaim


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


async def get_or_create_locked(session: AsyncSession, *, user_id: int, season_id: int) -> BattlePass:
    """Как get_or_create, но БЕЗ commit и с блокировкой строки (`SELECT ... FOR UPDATE`) —
    для использования ВНУТРИ составных транзакций (крутка/слияние), см.
    `services/battle_pass.add_progress`. Коммит остаётся за вызывающим сервисом верхнего
    уровня (правило 10, CLAUDE.md) — переиспользовать здесь `get_or_create` нельзя, та
    коммитит сама и преждевременно закрыла бы транзакцию крутки/слияния."""
    stmt = select(BattlePass).where(BattlePass.user_id == user_id, BattlePass.season_id == season_id).with_for_update()
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is not None:
        return row

    insert_stmt = (
        pg_insert(BattlePass)
        .values(user_id=user_id, season_id=season_id)
        .on_conflict_do_nothing(index_elements=[BattlePass.user_id, BattlePass.season_id])
        .returning(BattlePass)
    )
    row = (await session.execute(insert_stmt)).scalar_one_or_none()
    if row is None:
        # Конкурент вставил первым между нашим SELECT и INSERT — перечитываем с блокировкой.
        row = (await session.execute(stmt)).scalar_one()
    return row


async def update_progress(
    session: AsyncSession,
    *,
    user_id: int,
    season_id: int,
    progress: int,
    boost_levels_used_today: int,
    boost_date: date,
) -> None:
    """Не коммитит — часть составной операции (см. `services/battle_pass.add_progress`)."""
    await session.execute(
        update(BattlePass)
        .where(BattlePass.user_id == user_id, BattlePass.season_id == season_id)
        .values(progress=progress, boost_levels_used_today=boost_levels_used_today, boost_date=boost_date)
    )


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


async def set_claimed_level(session: AsyncSession, *, user_id: int, season_id: int, track: str, level: int) -> None:
    """Двигает high-water mark нужной ветки. Не коммитит — часть составной операции
    claim_level/claim_all (см. services/battle_pass)."""
    column = "claimed_free_level" if track == TRACK_FREE else "claimed_premium_level"
    await session.execute(
        update(BattlePass)
        .where(BattlePass.user_id == user_id, BattlePass.season_id == season_id)
        .values({column: level})
    )


async def list_claims(session: AsyncSession, *, user_id: int, season_id: int, track: str) -> set[int]:
    """Уровни, забранные ВНЕ ОЧЕРЕДИ (см. docstring BattlePassClaim) — обычно пустое
    множество или несколько штук, не вся история клеймов."""
    result = await session.execute(
        select(BattlePassClaim.level).where(
            BattlePassClaim.user_id == user_id,
            BattlePassClaim.season_id == season_id,
            BattlePassClaim.track == track,
        )
    )
    return set(result.scalars().all())


async def claim_exists(session: AsyncSession, *, user_id: int, season_id: int, track: str, level: int) -> bool:
    return await session.get(BattlePassClaim, (user_id, season_id, track, level)) is not None


async def add_claim(session: AsyncSession, *, user_id: int, season_id: int, track: str, level: int) -> None:
    """Не коммитит — часть claim_level. ON CONFLICT DO NOTHING — защита от двойного клика
    поверх Redis-лока (правило 2, CLAUDE.md), а не основная защита."""
    stmt = (
        pg_insert(BattlePassClaim)
        .values(user_id=user_id, season_id=season_id, track=track, level=level)
        .on_conflict_do_nothing(index_elements=[BattlePassClaim.user_id, BattlePassClaim.season_id, BattlePassClaim.track, BattlePassClaim.level])
    )
    await session.execute(stmt)


async def delete_claims(session: AsyncSession, *, user_id: int, season_id: int, track: str, levels: list[int]) -> None:
    """Не коммитит — используется при поглощении подряд идущих внеочередных клеймов в
    high-water mark, и при clear_claims ниже."""
    if not levels:
        return
    await session.execute(
        delete(BattlePassClaim).where(
            BattlePassClaim.user_id == user_id,
            BattlePassClaim.season_id == season_id,
            BattlePassClaim.track == track,
            BattlePassClaim.level.in_(levels),
        )
    )


async def clear_claims(session: AsyncSession, *, user_id: int, season_id: int, track: str) -> None:
    """Все внеочередные клеймы ветки становятся не нужны после claim_all (весь диапазон до
    текущего уровня уже забран через high-water mark). Не коммитит."""
    await session.execute(
        delete(BattlePassClaim).where(
            BattlePassClaim.user_id == user_id,
            BattlePassClaim.season_id == season_id,
            BattlePassClaim.track == track,
        )
    )
