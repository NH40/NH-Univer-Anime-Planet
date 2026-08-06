from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.constant.donate import TRANSACTION_REASON_DONATE
from bot.constant.referral import TRANSACTION_REASON_REFERRAL_DONATE_CUT, TRANSACTION_REASON_REFERRAL_REWARD
from bot.constant.shop import TRANSACTION_REASON_BATTLE_PASS, TRANSACTION_REASON_SUBSCRIPTION
from bot.db.repositories import referral as referral_repo
from bot.db.repositories.referral import CampaignStats

# Причины transactions.reason, которые считаются "заработком с рефералов" на экране
# профиля (см. handlers/profile: get_referral_stats) — награда рефереру за порог круток
# приглашённого (см. config/game.REFERRAL_ROLL_THRESHOLD) + % с его донатов.
REFERRAL_REWARD_REASONS = (TRANSACTION_REASON_REFERRAL_REWARD, TRANSACTION_REASON_REFERRAL_DONATE_CUT)


class ReferralCodeTakenError(Exception):
    pass


async def create_link(session: AsyncSession, *, code: str, admin_id: int) -> None:
    ok = await referral_repo.create(session, code=code, admin_id=admin_id)
    if not ok:
        raise ReferralCodeTakenError
    await session.commit()


async def record_visit(session: AsyncSession, *, code: str, user_id: int) -> None:
    """Молча игнорирует неизвестный код — битая/устаревшая реферальная ссылка не должна
    ронять /start (см. handlers/start)."""
    link = await referral_repo.get_by_code(session, code)
    if link is None:
        return
    await referral_repo.create_visit(session, code=code, user_id=user_id)
    await session.commit()


async def list_links_with_stats(session: AsyncSession) -> list[tuple[str, int, int]]:
    return await referral_repo.list_with_stats(session)


async def get_campaign_stats(session: AsyncSession, code: str) -> CampaignStats | None:
    return await referral_repo.get_campaign_stats(
        session,
        code,
        subscription_reason=TRANSACTION_REASON_SUBSCRIPTION,
        battle_pass_reason=TRANSACTION_REASON_BATTLE_PASS,
        donate_reason=TRANSACTION_REASON_DONATE,
    )
