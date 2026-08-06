from __future__ import annotations

import random
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import sync_score
from bot.config.game import (
    EVENT_CARD_CHANCE,
    REFERRAL_ROLL_REWARD_COINS,
    REFERRAL_ROLL_REWARD_TICKETS,
    REFERRAL_ROLL_THRESHOLD,
    ROLL_ONE_COST,
)
from bot.constant.gacha import TRANSACTION_REASON_ROLL
from bot.constant.referral import TRANSACTION_REASON_REFERRAL_REWARD
from bot.db.models.card import Card
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories.card import list_by_universe
from bot.db.repositories.inventory import add_card
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.user import add_coins, increment_total_rolls
from bot.services import event as event_service
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


async def roll_one(session: AsyncSession, redis: Redis, *, user_id: int, universe_code: str) -> RollResult:
    """Одна логическая операция — один commit в конце (см. CLAUDE.md, "Границы
    транзакций"): списание тикета, добавление карты в инвентарь и начисление UBP либо
    случаются все вместе, либо (при любой ошибке) откатываются все вместе.

    Крутка только по одной карте за раз — намеренно, x10 убрана (подтверждено
    пользователем 2026-08-06): цепочка одиночных круток с кнопкой "Крутить ещё" на экране
    результата затягивает сильнее, чем пачка результатов разом."""
    season = await get_active_season(session)
    if season is None:
        raise NoActiveSeasonError

    # Кидает UniverseNotReadyError, если во вселенной не заполнен один из тиров —
    # намеренно наружу, до списания тикетов (см. решение пользователя про пустые тиры).
    tier_map = await get_tier_map(session, universe_code)

    # Активный ивент действует ПОВЕРХ обычной крутки, независимо от выбранной вселенной
    # (см. CLAUDE.md, "Ивенты") — если под ивент ещё не залито ни одной карточки,
    # event_cards пуст и шанс естественно никогда не срабатывает, без отдельной проверки.
    active_event = await event_service.get_active(session)
    event_cards = await list_by_universe(session, active_event.universe_code) if active_event else []

    new_balance = await ticket.spend(session, user_id, ROLL_ONE_COST)
    if new_balance is None:
        raise NotEnoughTicketsError(needed=ROLL_ONE_COST)

    if event_cards and random.random() < EVENT_CARD_CHANCE:
        card = random.choice(event_cards)
    else:
        card = pick_card(tier_map)

    owned_quantity = await add_card(session, user_id=user_id, card_id=card.id, stars=1, qty=1)

    new_season_ubp = await award_ubp(session, user_id=user_id, amount=card.base_ubp, reason=TRANSACTION_REASON_ROLL)
    new_total_rolls, referred_by_id = await increment_total_rolls(session, user_id=user_id, amount=1)

    # new_total_rolls == REFERRAL_ROLL_THRESHOLD означает, что именно ЭТА крутка довела
    # приглашённого до порога — награда рефереру выдаётся ровно один раз (см. CLAUDE.md,
    # "Рефералы": порог, а не первая крутка — анти-абьюз пустыми/брошенными аккаунтами).
    if referred_by_id is not None and new_total_rolls == REFERRAL_ROLL_THRESHOLD:
        await add_coins(session, user_id=referred_by_id, amount=REFERRAL_ROLL_REWARD_COINS)
        await ticket.grant(session, referred_by_id, REFERRAL_ROLL_REWARD_TICKETS)
        session.add(
            Transaction(
                user_id=referred_by_id,
                currency=TransactionCurrency.coins,
                amount=REFERRAL_ROLL_REWARD_COINS,
                reason=TRANSACTION_REASON_REFERRAL_REWARD,
            )
        )
        session.add(
            Transaction(
                user_id=referred_by_id,
                currency=TransactionCurrency.tickets,
                amount=REFERRAL_ROLL_REWARD_TICKETS,
                reason=TRANSACTION_REASON_REFERRAL_REWARD,
            )
        )

    await session.commit()
    # Redis обновляем только после успешного commit в Postgres (см. CLAUDE.md, правило 10).
    await sync_score(redis, season.id, user_id, new_season_ubp)

    return RollResult(card=card, owned_quantity=owned_quantity)
