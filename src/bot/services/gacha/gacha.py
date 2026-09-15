from __future__ import annotations

import random
from dataclasses import dataclass

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.cache.leaderboard import sync_score
from bot.cache.universe_leaderboard import sync_score as sync_universe_score
from bot.config.game import (
    CELESTIAL_CARD_STARS,
    CELESTIAL_DROP_CHANCE,
    EVENT_CARD_CHANCE,
    REFERRAL_ROLL_REWARD_COINS,
    REFERRAL_ROLL_REWARD_TICKETS,
    REFERRAL_ROLL_THRESHOLD,
    ROLL_ONE_COST,
)
from bot.constant.celestial import TRANSACTION_REASON_CELESTIAL_DROP
from bot.constant.gacha import TRANSACTION_REASON_ROLL
from bot.constant.referral import TRANSACTION_REASON_REFERRAL_REWARD
from bot.db.models.card import Card
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories.card import list_by_universe
from bot.db.repositories.inventory import add_card
from bot.db.repositories.season import get_active as get_active_season
from bot.db.repositories.user import add_coins, increment_total_rolls
from bot.services import battle_pass as pass_service
from bot.services import celestial as celestial_service
from bot.services import event as event_service
from bot.services import ticket
from bot.services.card import get_tier_map, pick_card
from bot.services.ubp import UbpAward, award_ubp


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
    # Небесные карты (см. CLAUDE.md, "Небесные карты") — заполнено, только если card.is_celestial:
    # "owner" (первый дроп — игрок сразу владелец) или "challenger" (карта уже была у
    # кого-то — игрок стал претендентом, физической копии пока не получил).
    celestial_outcome: str | None = None
    celestial_current_owner_id: int | None = None  # кому слать пуш accept/decline, если challenger
    # Божественные карты, которые могла заодно принести эта же крутка (см.
    # services/celestial.check_universe_completion/check_global_divine) — хендлер
    # показывает игроку отдельное уведомление, если не None.
    universe_divine_card: Card | None = None
    global_divine_card: Card | None = None


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

    # Небесные карты этой вселенной, на которые эта крутка МОГЛА БЫ попасть (слот свободен
    # или у него ещё нет претендента, см. CLAUDE.md, "Небесные карты") — читаем ДО списания
    # тикета, тем же порядком, что ивент-карты выше.
    eligible_celestial = await celestial_service.list_eligible_drop_cards(
        session, universe_code=universe_code, roller_id=user_id
    )

    new_balance = await ticket.spend(session, user_id, ROLL_ONE_COST)
    if new_balance is None:
        raise NotEnoughTicketsError(needed=ROLL_ONE_COST)

    celestial_outcome = None  # DropOutcome | None
    if eligible_celestial and random.random() < CELESTIAL_DROP_CHANCE:
        candidate = random.choice(eligible_celestial)
        celestial_outcome = await celestial_service.resolve_drop(session, card=candidate, user_id=user_id)
        card = candidate if celestial_outcome is not None else None
    else:
        card = None

    if card is None and event_cards and random.random() < EVENT_CARD_CHANCE:
        card = random.choice(event_cards)
        celestial_outcome = None
    if card is None:
        card = pick_card(tier_map)
        celestial_outcome = None

    became_challenger = celestial_outcome is not None and not celestial_outcome.became_owner
    if became_challenger:
        owned_quantity = 0  # претендент физической копии карты ещё не получает
    else:
        stars = CELESTIAL_CARD_STARS if card.is_celestial else 1
        owned_quantity = await add_card(session, user_id=user_id, card_id=card.id, stars=stars, qty=1)

    reason = TRANSACTION_REASON_CELESTIAL_DROP if card.is_celestial else TRANSACTION_REASON_ROLL
    roll_award: UbpAward = await award_ubp(
        session, user_id=user_id, amount=card.base_ubp, reason=reason, universe_code=card.universe_code
    )
    await pass_service.add_progress(session, user_id=user_id, season_id=season.id, real_ubp=card.base_ubp)

    universe_divine_card: Card | None = None
    global_divine_card: Card | None = None
    divine_award: UbpAward | None = None
    if card.is_celestial and celestial_outcome is not None and celestial_outcome.became_owner:
        # Только СВЕЖИЙ дроп может закрыть "все 10 одновременно" — претендент ещё не
        # владеет картой, значит его набор владений не изменился.
        divine_res = await celestial_service.check_global_divine(session, user_id=user_id, season_id=season.id)
        if divine_res is not None:
            global_divine_card, divine_award = divine_res
    elif not card.is_celestial and not card.is_divine:
        completion_res = await celestial_service.check_universe_completion(
            session, user_id=user_id, universe_code=card.universe_code, season_id=season.id
        )
        if completion_res is not None:
            universe_divine_card, divine_award = completion_res
    divine_card = universe_divine_card or global_divine_card
    # Последнее начисление ubp_season за эту крутку целиком (обычная карта, плюс
    # божественная поверх неё, если досталась) — накопительный счётчик, синхронизации по
    # ОБЩЕМУ UBP достаточно самого свежего значения.
    latest_ubp_season = divine_award.ubp_season if divine_award is not None else roll_award.ubp_season

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
    await sync_score(redis, season.id, user_id, latest_ubp_season)
    if divine_card is not None and divine_card.universe_code == card.universe_code:
        # Божественная досталась в ТОЙ ЖЕ вселенной, что и сама крутка — divine_award уже
        # накопительно включает оба начисления по этой вселенной (тот же ряд обновлялся
        # дважды подряд в одной транзакции), синк один, самым свежим значением.
        await sync_universe_score(redis, season.id, card.universe_code, user_id, divine_award.universe_ubp_season)
    else:
        await sync_universe_score(redis, season.id, card.universe_code, user_id, roll_award.universe_ubp_season)
        if divine_card is not None:
            await sync_universe_score(redis, season.id, divine_card.universe_code, user_id, divine_award.universe_ubp_season)

    return RollResult(
        card=card,
        stars=CELESTIAL_CARD_STARS if card.is_celestial and not became_challenger else 1,
        owned_quantity=owned_quantity,
        celestial_outcome=(
            None if celestial_outcome is None else ("owner" if celestial_outcome.became_owner else "challenger")
        ),
        celestial_current_owner_id=celestial_outcome.current_owner_id if celestial_outcome else None,
        universe_divine_card=universe_divine_card,
        global_divine_card=global_divine_card,
    )
