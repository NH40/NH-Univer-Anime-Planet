from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import sync_score
from bot.config.game import MERGE_COPIES_REQUIRED, ubp_for_stars
from bot.constant.merge import TRANSACTION_REASON_MERGE
from bot.db.models.card import Card
from bot.db.repositories.card import get_by_id as get_card_by_id
from bot.db.repositories.inventory import add_card, decrement_by
from bot.db.repositories.season import get_active as get_active_season
from bot.services.ubp import award_ubp


class CardNotFoundError(Exception):
    pass


class NotEnoughCopiesError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NoActiveSeasonError(Exception):
    pass


@dataclass
class MergeResult:
    card: Card
    new_stars: int
    new_ubp: int
    bonus_ubp: int


async def merge_stack(
    session: AsyncSession, redis: Redis, *, user_id: int, card_id: int, stars: int
) -> MergeResult:
    """5 копий (card_id, stars) -> 1 копия (card_id, stars+1). Начисляет только РАЗНИЦУ
    UBP (см. CLAUDE.md, "Модель начисления UBP") — она всегда равна UBP одной исходной
    карты, т.е. `ubp_for_stars(base_ubp, stars)`. Одна логическая операция — один commit
    в конце (см. правило 10): списание пяти копий, выдача новой карты и начисление UBP
    случаются вместе или не случаются вовсе."""
    card = await get_card_by_id(session, card_id)
    if card is None:
        raise CardNotFoundError(card_id)

    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    ok = await decrement_by(
        session, user_id=user_id, card_id=card_id, stars=stars, amount=MERGE_COPIES_REQUIRED
    )
    if not ok:
        raise NotEnoughCopiesError(needed=MERGE_COPIES_REQUIRED)

    new_stars = stars + 1
    await add_card(session, user_id=user_id, card_id=card_id, stars=new_stars, qty=1)

    bonus = ubp_for_stars(card.base_ubp, stars)  # UBP одной исходной карты — см. CLAUDE.md
    new_season_ubp = await award_ubp(session, user_id=user_id, amount=bonus, reason=TRANSACTION_REASON_MERGE)

    await session.commit()
    # Redis обновляем только после успешного commit в Postgres (см. CLAUDE.md, правило 10).
    await sync_score(redis, season.id, user_id, new_season_ubp)

    return MergeResult(
        card=card,
        new_stars=new_stars,
        new_ubp=ubp_for_stars(card.base_ubp, new_stars),
        bonus_ubp=bonus,
    )


async def merge_all(
    session: AsyncSession, redis: Redis, *, user_id: int, card_id: int, stars: int
) -> list[MergeResult]:
    """Сливает (card_id, stars) сколько раз подряд получится из имеющихся копий, БЕЗ
    каскада в следующую звезду — если после этого у (card_id, stars+1) тоже накопится 5+,
    слить их можно отдельным нажатием уже на ЕЁ стопке (та же граница, что у обычного
    "Слить 5→1", просто повторённая). Одна логическая операция на весь пакет — один
    commit в конце (правило 10), но `award_ubp` вызывается ОТДЕЛЬНО на каждое слияние (не
    один раз суммой) — иначе живая агрегация ежедневных заданий по count(transactions)
    (см. CLAUDE.md, "Ежедневные задания") видела бы "Слить всё" как ОДНО слияние вместо
    N, недосчитывая прогресс quest'а "Смержи карты N раз" (было исправлено 2026-08-06,
    после того как игрок сообщил, что "выполненное" задание не давало забрать награду)."""
    card = await get_card_by_id(session, card_id)
    if card is None:
        raise CardNotFoundError(card_id)

    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    new_stars = stars + 1
    bonus = ubp_for_stars(card.base_ubp, stars)  # UBP одной исходной карты — см. CLAUDE.md
    results: list[MergeResult] = []
    new_season_ubp = None

    while await decrement_by(session, user_id=user_id, card_id=card_id, stars=stars, amount=MERGE_COPIES_REQUIRED):
        await add_card(session, user_id=user_id, card_id=card_id, stars=new_stars, qty=1)
        new_season_ubp = await award_ubp(session, user_id=user_id, amount=bonus, reason=TRANSACTION_REASON_MERGE)
        results.append(
            MergeResult(card=card, new_stars=new_stars, new_ubp=ubp_for_stars(card.base_ubp, new_stars), bonus_ubp=bonus)
        )

    if not results:
        raise NotEnoughCopiesError(needed=MERGE_COPIES_REQUIRED)

    await session.commit()
    await sync_score(redis, season.id, user_id, new_season_ubp)
    return results
