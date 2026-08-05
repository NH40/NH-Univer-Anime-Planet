from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.referral import ReferralLink, ReferralVisit
from bot.db.models.user import User


async def get_by_code(session: AsyncSession, code: str) -> ReferralLink | None:
    return await session.get(ReferralLink, code)


async def create(session: AsyncSession, *, code: str, admin_id: int) -> bool:
    """Атомарный insert — False, если название кампании уже занято. Не коммитит."""
    stmt = (
        pg_insert(ReferralLink)
        .values(code=code, admin_id=admin_id)
        .on_conflict_do_nothing(index_elements=[ReferralLink.code])
        .returning(ReferralLink.code)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_visit(session: AsyncSession, *, code: str, user_id: int) -> bool:
    """Атомарный insert — PK по user_id гарантирует "первый переход побеждает"
    (см. db/models/referral.py). Не коммитит."""
    stmt = (
        pg_insert(ReferralVisit)
        .values(user_id=user_id, link_code=code)
        .on_conflict_do_nothing(index_elements=[ReferralVisit.user_id])
        .returning(ReferralVisit.user_id)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none() is not None


async def list_with_stats(session: AsyncSession) -> list[tuple[str, int, int]]:
    """(код, перешло, играет = ubp_season > 0) для всех кампаний одним запросом
    (не по одному на ссылку — правило 3)."""
    stmt = (
        select(
            ReferralLink.code,
            func.count(ReferralVisit.user_id),
            func.count(ReferralVisit.user_id).filter(User.ubp_season > 0),
        )
        .select_from(ReferralLink)
        .outerjoin(ReferralVisit, ReferralVisit.link_code == ReferralLink.code)
        .outerjoin(User, User.id == ReferralVisit.user_id)
        .group_by(ReferralLink.code)
        .order_by(ReferralLink.created_at.desc())
    )
    result = await session.execute(stmt)
    return [(code, int(visited), int(playing)) for code, visited, playing in result.all()]
