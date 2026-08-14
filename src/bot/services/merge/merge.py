from __future__ import annotations

from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import sync_score
from bot.config.game import MAX_STARS, MERGE_COPIES_REQUIRED, ubp_for_stars
from bot.constant.merge import TRANSACTION_REASON_MERGE
from bot.db.models.card import Card
from bot.db.repositories.card import get_by_id as get_card_by_id
from bot.db.repositories.inventory import add_card, decrement_by, list_owned_stacks_in_universe
from bot.db.repositories.season import get_active as get_active_season
from bot.services import battle_pass as pass_service
from bot.services.ubp import award_ubp


class CardNotFoundError(Exception):
    pass


class NotEnoughCopiesError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NoActiveSeasonError(Exception):
    pass


class InvalidTargetError(Exception):
    """target_stars вне допустимого диапазона (не выше stars, либо выше MAX_STARS)."""


@dataclass
class MergeSummary:
    """Итог одной операции слияния (единичной "1 карта -> X★" или каскада "все карты
    -> X★"): сколько РЕАЛЬНЫХ 5->1 событий произошло (важно для count-based квеста
    "Смержи карты N раз", см. CLAUDE.md), какая итоговая звезда и суммарный бонус UBP."""

    card: Card
    final_stars: int
    events: int
    total_bonus: int


async def _cascade_all(
    session: AsyncSession, *, user_id: int, card: Card, season_id: int, stars: int, target_stars: int
) -> tuple[MergeSummary | None, int | None]:
    """Сливает ВСЕ копии `stars`, каскадом, не поднимаясь выше `target_stars`. Не
    коммитит — вызывающая функция коммитит один раз в конце (правило 10). Возвращает
    (сводка или None, если ничего не смёрджилось; последний ubp_season после award_ubp)."""
    total_events = 0
    total_bonus = 0
    final_stars = stars
    new_season_ubp: int | None = None

    level = stars
    while level < target_stars:
        merged_here = 0
        while await decrement_by(session, user_id=user_id, card_id=card.id, stars=level, amount=MERGE_COPIES_REQUIRED):
            new_level = level + 1
            await add_card(session, user_id=user_id, card_id=card.id, stars=new_level, qty=1)
            bonus = ubp_for_stars(card.base_ubp, level)
            new_season_ubp = await award_ubp(session, user_id=user_id, amount=bonus, reason=TRANSACTION_REASON_MERGE)
            await pass_service.add_progress(session, user_id=user_id, season_id=season_id, real_ubp=bonus)
            total_events += 1
            total_bonus += bonus
            final_stars = new_level
            merged_here += 1
        if merged_here == 0:
            break
        level += 1

    if total_events == 0:
        return None, None
    return MergeSummary(card=card, final_stars=final_stars, events=total_events, total_bonus=total_bonus), new_season_ubp


async def merge_to_target(
    session: AsyncSession,
    redis: Redis,
    *,
    user_id: int,
    card_id: int,
    stars: int,
    target_stars: int,
    single: bool,
) -> MergeSummary:
    """single=True — ровно MERGE_COPIES_REQUIRED**(target_stars-stars) копий -> 1 карта
    target_stars, без остатка (промежуточные "виртуальные" копии на пути к target_stars
    никогда реально не лежат в инвентаре — каскад считается в Python, в БД идёт только
    начальное списание и финальная выдача). single=False — каскад из ВСЕХ копий `stars`,
    не поднимаясь выше `target_stars` (см. CLAUDE.md, "Слияния"). Одна логическая
    операция — один commit, но award_ubp вызывается на КАЖДОЕ фактическое 5->1 событие,
    не суммой (квест "Смержи карты N раз" считает строки transactions, см. CLAUDE.md)."""
    if target_stars <= stars or target_stars > MAX_STARS or stars >= MAX_STARS:
        raise InvalidTargetError

    card = await get_card_by_id(session, card_id)
    if card is None:
        raise CardNotFoundError(card_id)

    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    if single:
        required = MERGE_COPIES_REQUIRED ** (target_stars - stars)
        ok = await decrement_by(session, user_id=user_id, card_id=card_id, stars=stars, amount=required)
        if not ok:
            raise NotEnoughCopiesError(needed=required)

        qty = required
        total_events = 0
        total_bonus = 0
        new_season_ubp: int | None = None
        for level in range(stars, target_stars):
            n_events = qty // MERGE_COPIES_REQUIRED
            bonus_per_event = ubp_for_stars(card.base_ubp, level)
            for _ in range(n_events):
                new_season_ubp = await award_ubp(
                    session, user_id=user_id, amount=bonus_per_event, reason=TRANSACTION_REASON_MERGE
                )
                await pass_service.add_progress(session, user_id=user_id, season_id=season.id, real_ubp=bonus_per_event)
            total_events += n_events
            total_bonus += n_events * bonus_per_event
            qty = n_events
        await add_card(session, user_id=user_id, card_id=card_id, stars=target_stars, qty=1)

        await session.commit()
        await sync_score(redis, season.id, user_id, new_season_ubp)
        return MergeSummary(card=card, final_stars=target_stars, events=total_events, total_bonus=total_bonus)

    summary, new_season_ubp = await _cascade_all(
        session, user_id=user_id, card=card, season_id=season.id, stars=stars, target_stars=target_stars
    )
    if summary is None:
        raise NotEnoughCopiesError(needed=MERGE_COPIES_REQUIRED)

    await session.commit()
    await sync_score(redis, season.id, user_id, new_season_ubp)
    return summary


async def merge_all_to_max_in_universe(
    session: AsyncSession, redis: Redis, *, user_id: int, universe_code: str
) -> list[MergeSummary]:
    """Балк-версия "Слить всё до Макс" с тир-пикера — по каждой стопке (card, stars)
    вселенной с quantity >= MERGE_COPIES_REQUIRED и stars < MAX_STARS каскадом сливает
    всё возможное до MAX_STARS (не выходя за пределы одной вселенной; ивент-карты не
    входят — доступны отдельно через обычный выбор карты). Одна логическая операция на
    весь пакет — один commit в конце."""
    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    stacks = await list_owned_stacks_in_universe(session, user_id=user_id, universe_code=universe_code)
    eligible = [s for s in stacks if s.stars < MAX_STARS and s.quantity >= MERGE_COPIES_REQUIRED]

    summaries: list[MergeSummary] = []
    last_season_ubp: int | None = None
    for stack in eligible:
        summary, new_season_ubp = await _cascade_all(
            session, user_id=user_id, card=stack.card, season_id=season.id, stars=stack.stars, target_stars=MAX_STARS
        )
        if summary is not None:
            summaries.append(summary)
            last_season_ubp = new_season_ubp

    if not summaries:
        return []

    await session.commit()
    await sync_score(redis, season.id, user_id, last_season_ubp)
    return summaries
