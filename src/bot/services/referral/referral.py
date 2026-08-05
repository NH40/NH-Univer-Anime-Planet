from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import referral as referral_repo


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
