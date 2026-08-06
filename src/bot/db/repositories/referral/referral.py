from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.referral import ReferralLink, ReferralVisit
from bot.db.models.transaction import Transaction
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


@dataclass
class CampaignStats:
    code: str
    visited: int
    playing: int  # ubp_season > 0
    subscriptions_bought: int
    battle_passes_bought: int
    donated_coins: int  # = рубли, донат 1:1 (см. CLAUDE.md, "Донат")


async def get_campaign_stats(
    session: AsyncSession,
    code: str,
    *,
    subscription_reason: str,
    battle_pass_reason: str,
    donate_reason: str,
) -> CampaignStats | None:
    """Детальная статистика по ОДНОЙ именной кампании (см. handlers/admin/referral —
    экран-детализация). Reason-константы приходят параметрами из services/referral, а не
    импортируются здесь напрямую — тот же принцип, что у get_referral_stats в
    db/repositories/user (config/constant читается в сервисном слое, репозиторий их не
    знает). Несколько небольших запросов вместо одного гигантского JOIN — не горячий путь
    (один админ открывает статистику одной кампании по кнопке), читаемость важнее."""
    link = await get_by_code(session, code)
    if link is None:
        return None

    visited_stmt = (
        select(
            func.count(ReferralVisit.user_id),
            func.count(ReferralVisit.user_id).filter(User.ubp_season > 0),
        )
        .select_from(ReferralVisit)
        .join(User, User.id == ReferralVisit.user_id)
        .where(ReferralVisit.link_code == code)
    )
    visited, playing = (await session.execute(visited_stmt)).one()

    referred_ids = select(ReferralVisit.user_id).where(ReferralVisit.link_code == code)
    tx_stmt = (
        select(
            func.count().filter(Transaction.reason == subscription_reason),
            func.count().filter(Transaction.reason == battle_pass_reason),
            func.coalesce(func.sum(Transaction.amount).filter(Transaction.reason == donate_reason), 0),
        )
        .select_from(Transaction)
        .where(Transaction.user_id.in_(referred_ids))
    )
    subscriptions_bought, battle_passes_bought, donated_coins = (await session.execute(tx_stmt)).one()

    return CampaignStats(
        code=code,
        visited=int(visited),
        playing=int(playing),
        subscriptions_bought=int(subscriptions_bought),
        battle_passes_bought=int(battle_passes_bought),
        donated_coins=int(donated_coins),
    )


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
