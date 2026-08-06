from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import sync_score
from bot.config.game import REFERRAL_FIRST_ROLL_REWARD_COINS, REFERRAL_FIRST_ROLL_REWARD_TICKETS, ROLL_ONE_COST, ROLL_TEN_COST, ROLL_TEN_COUNT
from bot.constant.gacha import TRANSACTION_REASON_ROLL
from bot.constant.referral import TRANSACTION_REASON_REFERRAL_REWARD
from bot.db.models.card import Card
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories.inventory import add_card
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.user import add_coins, increment_total_rolls
from bot.services import ticket
from bot.services.card import get_tier_map, pick_card
from bot.services.ubp import award_ubp


class NotEnoughTicketsError(Exception):
    def __init__(self, needed: int) -> None:
        self.needed = needed


class NoActiveSeasonError(Exception):
    pass


@dataclass
class RollResult:
    card: Card
    stars: int = 1  # всегда 1 сразу после крутки — звёзды растут только слиянием
    owned_quantity: int = 1  # сколько копий этой карты (этой звезды) теперь у игрока всего


async def _roll(
    session: AsyncSession, redis: Redis, *, user_id: int, universe_code: str, count: int, cost: int
) -> list[RollResult]:
    """Одна логическая операция — один commit в конце (см. CLAUDE.md, "Границы
    транзакций"): списание тикетов, добавление карт в инвентарь и начисление UBP либо
    случаются все вместе, либо (при любой ошибке) откатываются все вместе."""
    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    # Кидает UniverseNotReadyError, если во вселенной не заполнен один из тиров —
    # намеренно наружу, до списания тикетов (см. решение пользователя про пустые тиры).
    tier_map = await get_tier_map(session, universe_code)

    new_balance = await ticket.spend(session, user_id, cost)
    if new_balance is None:
        raise NotEnoughTicketsError(needed=cost)

    cards = [pick_card(tier_map) for _ in range(count)]

    # Группируем повторки внутри одной крутки x10 в один upsert на card_id — меньше
    # запросов к БД (правило 3), чем по одному апсерту на каждую из 10 карт.
    counts = Counter(card.id for card in cards)
    owned_quantity_by_card_id: dict[int, int] = {}
    for card_id, qty in counts.items():
        owned_quantity_by_card_id[card_id] = await add_card(session, user_id=user_id, card_id=card_id, stars=1, qty=qty)

    total_ubp = sum(card.base_ubp for card in cards)
    new_season_ubp = await award_ubp(session, user_id=user_id, amount=total_ubp, reason=TRANSACTION_REASON_ROLL)
    new_total_rolls, referred_by_id = await increment_total_rolls(session, user_id=user_id, amount=count)

    # new_total_rolls == count означает, что ДО этой крутки было 0 — то есть она первая
    # вообще (см. CLAUDE.md, "Рефералы": награда рефереру только за первую крутку
    # приглашённого, не за каждую — анти-абьюз пустыми аккаунтами).
    if referred_by_id is not None and new_total_rolls == count:
        await add_coins(session, user_id=referred_by_id, amount=REFERRAL_FIRST_ROLL_REWARD_COINS)
        await ticket.grant(session, referred_by_id, REFERRAL_FIRST_ROLL_REWARD_TICKETS)
        session.add(
            Transaction(
                user_id=referred_by_id,
                currency=TransactionCurrency.coins,
                amount=REFERRAL_FIRST_ROLL_REWARD_COINS,
                reason=TRANSACTION_REASON_REFERRAL_REWARD,
            )
        )
        session.add(
            Transaction(
                user_id=referred_by_id,
                currency=TransactionCurrency.tickets,
                amount=REFERRAL_FIRST_ROLL_REWARD_TICKETS,
                reason=TRANSACTION_REASON_REFERRAL_REWARD,
            )
        )

    await session.commit()
    # Redis обновляем только после успешного commit в Postgres (см. CLAUDE.md, правило 10).
    await sync_score(redis, season.id, user_id, new_season_ubp)

    return [RollResult(card=card, owned_quantity=owned_quantity_by_card_id[card.id]) for card in cards]


async def roll_one(session: AsyncSession, redis: Redis, *, user_id: int, universe_code: str) -> RollResult:
    results = await _roll(
        session, redis, user_id=user_id, universe_code=universe_code, count=1, cost=ROLL_ONE_COST
    )
    return results[0]


async def roll_ten(
    session: AsyncSession, redis: Redis, *, user_id: int, universe_code: str
) -> list[RollResult]:
    return await _roll(
        session, redis, user_id=user_id, universe_code=universe_code, count=ROLL_TEN_COUNT, cost=ROLL_TEN_COST
    )
