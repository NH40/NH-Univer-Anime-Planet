from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models.card import Card


async def list_by_universe(session: AsyncSession, universe_code: str) -> list[Card]:
    result = await session.execute(
        select(Card).where(Card.universe_code == universe_code).order_by(Card.base_ubp.desc(), Card.external_id)
    )
    return list(result.scalars().all())


async def get_by_id(session: AsyncSession, card_id: int) -> Card | None:
    return await session.get(Card, card_id)


async def get_discovered_card_ids(session: AsyncSession, user_id: int, universe_code: str) -> set[int]:
    """id всех карт этой вселенной, которые игрок хоть раз выбивал (для экрана "Шансы" —
    там нужно показывать "???" вместо имени ещё не открытого персонажа). Одним запросом
    на всю вселенную, а не по одному на тир — меньше обращений к БД (правило 3)."""
    from bot.db.models.inventory import UserCard  # локальный импорт — избегаем цикла

    result = await session.execute(
        select(Card.id)
        .join(UserCard, UserCard.card_id == Card.id)
        .where(Card.universe_code == universe_code, UserCard.user_id == user_id)
    )
    return {row[0] for row in result.all()}
