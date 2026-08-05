from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.enums import PromoCodeType
from bot.db.models.promocode import PromoCode, PromoRedemption


async def get_by_code(session: AsyncSession, code: str) -> PromoCode | None:
    return await session.get(PromoCode, code)


async def create(
    session: AsyncSession,
    *,
    code: str,
    type_: PromoCodeType,
    max_uses: int | None,
    expires_at: datetime | None,
    allowed_usernames: list[str] | None,
    reward: dict,
) -> bool:
    """Атомарный insert — False, если код уже занят. Не коммитит — вызывающий сервис
    коммитит сам (leaf-операция, но пусть решает сервис для единообразия с остальными
    admin-действиями)."""
    stmt = (
        pg_insert(PromoCode)
        .values(
            code=code,
            type=type_,
            max_uses=max_uses,
            expires_at=expires_at,
            allowed_usernames=allowed_usernames,
            reward=reward,
        )
        .on_conflict_do_nothing(index_elements=[PromoCode.code])
        .returning(PromoCode.code)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_redemption(session: AsyncSession, *, code: str, user_id: int) -> bool:
    """Атомарный insert — False, если этот игрок уже активировал этот код раньше.
    Не коммитит — часть составной операции redeem (см. services/promo)."""
    stmt = (
        pg_insert(PromoRedemption)
        .values(promo_code=code, user_id=user_id)
        .on_conflict_do_nothing(index_elements=[PromoRedemption.promo_code, PromoRedemption.user_id])
        .returning(PromoRedemption.id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def increment_used_count(session: AsyncSession, *, code: str) -> bool:
    """Атомарный инкремент с проверкой лимита ПРЯМО в WHERE (против текущего состояния
    строки, не снимка, прочитанного раньше) — False, если лимит уже исчерпан. Не коммитит."""
    stmt = (
        update(PromoCode)
        .where(PromoCode.code == code)
        .where(or_(PromoCode.max_uses.is_(None), PromoCode.used_count < PromoCode.max_uses))
        .values(used_count=PromoCode.used_count + 1)
        .returning(PromoCode.used_count)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None
