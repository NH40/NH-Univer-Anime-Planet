from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    BATTLE_PASS_MAX_LEVEL,
    battle_pass_cumulative_ubp,
    battle_pass_free_reward,
    battle_pass_level_from_ubp,
    battle_pass_premium_reward,
)
from bot.constant.battle_pass import TRANSACTION_REASON_PASS_FREE, TRANSACTION_REASON_PASS_PREMIUM
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import battle_pass as pass_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import add_coins, add_dust, get_by_id
from bot.services import ticket


class NoSeasonActiveError(Exception):
    pass


class NotPremiumError(Exception):
    pass


class NothingToClaimError(Exception):
    pass


def _sum_free_reward(from_level_exclusive: int, to_level_inclusive: int) -> tuple[int, int]:
    total_dust = total_tickets = 0
    for lvl in range(from_level_exclusive + 1, to_level_inclusive + 1):
        dust, tickets = battle_pass_free_reward(lvl)
        total_dust += dust
        total_tickets += tickets
    return total_dust, total_tickets


def _sum_premium_reward(from_level_exclusive: int, to_level_inclusive: int) -> tuple[int, int, int]:
    total_dust = total_tickets = total_coins = 0
    for lvl in range(from_level_exclusive + 1, to_level_inclusive + 1):
        dust, tickets, coins = battle_pass_premium_reward(lvl)
        total_dust += dust
        total_tickets += tickets
        total_coins += coins
    return total_dust, total_tickets, total_coins


@dataclass
class PassView:
    level: int
    ubp_season: int
    ubp_level_floor: int  # сколько UBP нужно было, чтобы достичь текущего уровня
    ubp_next_level_ceiling: int | None  # сколько нужно для следующего; None — уже максимум
    is_premium: bool
    claimed_free_level: int
    claimed_premium_level: int
    free_claimable: bool
    premium_claimable: bool
    # Сумма НЕЗАБРАННЫХ наград от последнего забранного уровня до текущего — то же самое,
    # что claim_free/claim_premium реально начислят по кнопке "Забрать" (см. CLAUDE.md,
    # "Сезонный пасс" — "одной кнопкой сразу все уровни"). Показываем на экране заранее,
    # чтобы игрок видел, что именно получит, до нажатия.
    pending_free_dust: int
    pending_free_tickets: int
    pending_premium_dust: int
    pending_premium_tickets: int
    pending_premium_coins: int


async def get_pass_view(session: AsyncSession, *, user_id: int) -> PassView | None:
    season = await season_repo.get_active(session)
    if season is None:
        return None

    user = await get_by_id(session, user_id)
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)

    level = battle_pass_level_from_ubp(user.ubp_season)
    floor = battle_pass_cumulative_ubp(level)
    ceiling = battle_pass_cumulative_ubp(level + 1) if level < BATTLE_PASS_MAX_LEVEL else None

    pending_free_dust, pending_free_tickets = _sum_free_reward(row.claimed_free_level, level)
    if row.is_premium:
        pending_premium_dust, pending_premium_tickets, pending_premium_coins = _sum_premium_reward(
            row.claimed_premium_level, level
        )
    else:
        pending_premium_dust = pending_premium_tickets = pending_premium_coins = 0

    return PassView(
        level=level,
        ubp_season=user.ubp_season,
        ubp_level_floor=floor,
        ubp_next_level_ceiling=ceiling,
        is_premium=row.is_premium,
        claimed_free_level=row.claimed_free_level,
        claimed_premium_level=row.claimed_premium_level,
        free_claimable=level > row.claimed_free_level,
        premium_claimable=row.is_premium and level > row.claimed_premium_level,
        pending_free_dust=pending_free_dust,
        pending_free_tickets=pending_free_tickets,
        pending_premium_dust=pending_premium_dust,
        pending_premium_tickets=pending_premium_tickets,
        pending_premium_coins=pending_premium_coins,
    )


async def claim_free(session: AsyncSession, *, user_id: int) -> tuple[int, int]:
    """Начисляет ВСЕ неполученные награды бесплатной ветки разом (от последнего забранного
    уровня до текущего). Возвращает (пыль, тикеты). Одна логическая операция — один commit."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoSeasonActiveError

    user = await get_by_id(session, user_id)
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)

    level = battle_pass_level_from_ubp(user.ubp_season)
    if level <= row.claimed_free_level:
        raise NothingToClaimError

    total_dust, total_tickets = _sum_free_reward(row.claimed_free_level, level)

    if total_dust:
        await add_dust(session, user_id=user_id, amount=total_dust)
        session.add(
            Transaction(
                user_id=user_id, currency=TransactionCurrency.dust, amount=total_dust, reason=TRANSACTION_REASON_PASS_FREE
            )
        )
    if total_tickets:
        await ticket.grant(session, user_id, total_tickets)
        session.add(
            Transaction(
                user_id=user_id,
                currency=TransactionCurrency.tickets,
                amount=total_tickets,
                reason=TRANSACTION_REASON_PASS_FREE,
            )
        )

    await pass_repo.set_claimed_free_level(session, user_id=user_id, season_id=season.id, level=level)
    await session.commit()
    return total_dust, total_tickets


async def claim_premium(session: AsyncSession, *, user_id: int) -> tuple[int, int, int]:
    """Аналог claim_free для премиум-ветки — требует row.is_premium (см. docstring модели
    BattlePass). Возвращает (пыль, тикеты, коины)."""
    season = await season_repo.get_active(session)
    if season is None:
        raise NoSeasonActiveError

    user = await get_by_id(session, user_id)
    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if not row.is_premium:
        raise NotPremiumError

    level = battle_pass_level_from_ubp(user.ubp_season)
    if level <= row.claimed_premium_level:
        raise NothingToClaimError

    total_dust, total_tickets, total_coins = _sum_premium_reward(row.claimed_premium_level, level)

    if total_dust:
        await add_dust(session, user_id=user_id, amount=total_dust)
        session.add(
            Transaction(
                user_id=user_id,
                currency=TransactionCurrency.dust,
                amount=total_dust,
                reason=TRANSACTION_REASON_PASS_PREMIUM,
            )
        )
    if total_tickets:
        await ticket.grant(session, user_id, total_tickets)
        session.add(
            Transaction(
                user_id=user_id,
                currency=TransactionCurrency.tickets,
                amount=total_tickets,
                reason=TRANSACTION_REASON_PASS_PREMIUM,
            )
        )
    if total_coins:
        await add_coins(session, user_id=user_id, amount=total_coins)
        session.add(
            Transaction(
                user_id=user_id,
                currency=TransactionCurrency.coins,
                amount=total_coins,
                reason=TRANSACTION_REASON_PASS_PREMIUM,
            )
        )

    await pass_repo.set_claimed_premium_level(session, user_id=user_id, season_id=season.id, level=level)
    await session.commit()
    return total_dust, total_tickets, total_coins
