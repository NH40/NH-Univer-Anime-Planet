from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import (
    BATTLE_PASS_BOOST_TIER_LEVELS,
    BATTLE_PASS_CYCLE_LEVELS,
    battle_pass_boost_multiplier,
    battle_pass_cumulative,
    battle_pass_free_reward,
    battle_pass_level_from_progress,
    battle_pass_premium_reward,
)
from bot.constant.battle_pass import TRANSACTION_REASON_PASS_FREE, TRANSACTION_REASON_PASS_PREMIUM
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories import battle_pass as pass_repo
from bot.db.repositories import season as season_repo
from bot.db.repositories.user import add_coins, add_dust
from bot.services import ticket

LEVELS_PER_PAGE = 10
_DAILY_BOOST_CAP = BATTLE_PASS_BOOST_TIER_LEVELS[-1]


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
    progress: int  # BattlePass.progress — НЕ User.ubp_season, см. CLAUDE.md
    progress_level_floor: int  # сколько progress нужно было, чтобы достичь текущего уровня
    progress_next_level_ceiling: int  # сколько нужно для следующего — уровни не ограничены сверху
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

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)

    level = battle_pass_level_from_progress(row.progress)
    floor = battle_pass_cumulative(level)
    ceiling = battle_pass_cumulative(level + 1)

    pending_free_dust, pending_free_tickets = _sum_free_reward(row.claimed_free_level, level)
    if row.is_premium:
        pending_premium_dust, pending_premium_tickets, pending_premium_coins = _sum_premium_reward(
            row.claimed_premium_level, level
        )
    else:
        pending_premium_dust = pending_premium_tickets = pending_premium_coins = 0

    return PassView(
        level=level,
        progress=row.progress,
        progress_level_floor=floor,
        progress_next_level_ceiling=ceiling,
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

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)

    level = battle_pass_level_from_progress(row.progress)
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

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    if not row.is_premium:
        raise NotPremiumError

    level = battle_pass_level_from_progress(row.progress)
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


async def add_progress(session: AsyncSession, *, user_id: int, season_id: int, real_ubp: int) -> None:
    """Начисляет прогресс Battle Pass, ускоренный дневным бустом (см. CLAUDE.md, "Сезонный
    пасс: 500 циклических уровней") — вызывается ПАРАЛЛЕЛЬНО с `services.ubp.award_ubp` из
    тех же составных операций (крутка, слияние), той же транзакцией, без своего commit
    (правило 10) — коммитит вызывающий сервис верхнего уровня. НЕ трогает `User.ubp_season`:
    тот остаётся источником для лидерборда/войн кланов, буст касается только скорости
    заполнения Battle Pass.

    Осознанное упрощение: множитель берётся ОДИН раз на всё событие целиком (не
    пересчитывается по уровню внутри одного крупного начисления, теоретически пересекающего
    границу тира буста) — типичное начисление UBP за раз небольшое, риск заметного
    расхождения исчезающе мал, а honest per-level цикл сильно усложнил бы код без реальной
    пользы."""
    if real_ubp <= 0:
        return

    row = await pass_repo.get_or_create_locked(session, user_id=user_id, season_id=season_id)

    today = datetime.now(timezone.utc).date()
    used_today = row.boost_levels_used_today if row.boost_date == today else 0

    multiplier = battle_pass_boost_multiplier(used_today)
    boosted = real_ubp * multiplier

    old_level = battle_pass_level_from_progress(row.progress)
    new_progress = row.progress + boosted
    new_level = battle_pass_level_from_progress(new_progress)

    new_used_today = min(_DAILY_BOOST_CAP, used_today + (new_level - old_level))

    await pass_repo.update_progress(
        session,
        user_id=user_id,
        season_id=season_id,
        progress=new_progress,
        boost_levels_used_today=new_used_today,
        boost_date=today,
    )


@dataclass
class LevelEntry:
    level: int  # абсолютный номер уровня (растёт бесконечно, награда циклится по позиции)
    free_dust: int
    free_tickets: int
    premium_dust: int
    premium_tickets: int
    premium_coins: int
    unlocked: bool
    free_claimed: bool
    premium_claimed: bool


@dataclass
class LevelsPage:
    entries: list[LevelEntry]
    page: int
    total_pages: int
    current_level: int
    is_premium: bool


async def list_levels(session: AsyncSession, *, user_id: int, page: int) -> LevelsPage | None:
    """Пагинированная лента уровней текущего 500-уровневого круга (не всей бесконечной
    истории) — общая формула для бота и Mini App, ничего не дублируется на два стека.
    Уровни якорятся на ТЕКУЩИЙ круг игрока: если игрок уже прошёл цикл 500 уровней целиком,
    страница 1 показывает уровни (500×circle + 1)..(500×circle + 10), а не 1..10 — иначе
    статус "забрано"/"доступно" не совпадал бы с реальным `claimed_free_level`."""
    season = await season_repo.get_active(session)
    if season is None:
        return None

    row = await pass_repo.get_or_create(session, user_id=user_id, season_id=season.id)
    current_level = battle_pass_level_from_progress(row.progress)
    circle_offset = ((current_level - 1) // BATTLE_PASS_CYCLE_LEVELS) * BATTLE_PASS_CYCLE_LEVELS if current_level > 0 else 0

    total_pages = -(-BATTLE_PASS_CYCLE_LEVELS // LEVELS_PER_PAGE)
    page = max(1, min(page, total_pages))
    start_pos = (page - 1) * LEVELS_PER_PAGE + 1
    end_pos = min(start_pos + LEVELS_PER_PAGE - 1, BATTLE_PASS_CYCLE_LEVELS)

    entries = []
    for pos in range(start_pos, end_pos + 1):
        level = circle_offset + pos
        free_dust, free_tickets = battle_pass_free_reward(level)
        premium_dust, premium_tickets, premium_coins = battle_pass_premium_reward(level)
        entries.append(
            LevelEntry(
                level=level,
                free_dust=free_dust,
                free_tickets=free_tickets,
                premium_dust=premium_dust,
                premium_tickets=premium_tickets,
                premium_coins=premium_coins,
                unlocked=current_level >= level,
                free_claimed=row.claimed_free_level >= level,
                premium_claimed=row.claimed_premium_level >= level,
            )
        )

    return LevelsPage(
        entries=entries, page=page, total_pages=total_pages, current_level=current_level, is_premium=row.is_premium
    )
