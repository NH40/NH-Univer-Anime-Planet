from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.game import DAILY_BONUS_MAX_STREAK, daily_bonus_reward
from bot.constant.daily_bonus import TRANSACTION_REASON_DAILY_BONUS
from bot.db.models.enums import TransactionCurrency
from bot.db.models.transaction import Transaction
from bot.db.repositories.user import add_dust, get_by_id
from bot.services import ticket


class AlreadyClaimedError(Exception):
    pass


# Атомарно продвигает streak одним UPDATE (см. CLAUDE.md, паттерн из services/ticket):
# CTE считает новый streak по времени последнего сбора (FOR UPDATE — блокирует строку
# от гонки повторного клика), внешний UPDATE применяет его, только если new_streak не
# NULL (NULL — уже забирал в последние 24ч, WHERE в UPDATE исключает такую строку, 0
# строк обновлено, RETURNING ничего не вернёт).
_CLAIM_SQL = text(
    """
    WITH cur AS (
        SELECT
            CASE
                WHEN daily_bonus_claimed_at IS NULL THEN 1
                WHEN daily_bonus_claimed_at <= now() - INTERVAL '48 hours' THEN 1
                WHEN daily_bonus_claimed_at <= now() - INTERVAL '24 hours'
                    THEN LEAST(daily_bonus_streak + 1, :max_streak)
                ELSE NULL
            END AS new_streak
        FROM users
        WHERE id = :user_id
        FOR UPDATE
    )
    UPDATE users
    SET daily_bonus_streak = cur.new_streak, daily_bonus_claimed_at = now()
    FROM cur
    WHERE users.id = :user_id AND cur.new_streak IS NOT NULL
    RETURNING cur.new_streak
    """
)


@dataclass
class DailyBonusClaim:
    day: int
    dust: int
    tickets: int


async def claim(session: AsyncSession, *, user_id: int) -> DailyBonusClaim:
    """Продвигает streak и сразу начисляет награду за новый день — одна логическая
    операция, один commit (см. CLAUDE.md, правило 10). Бросает AlreadyClaimedError, если
    бонус уже забирали в последние 24ч."""
    result = await session.execute(_CLAIM_SQL, {"user_id": user_id, "max_streak": DAILY_BONUS_MAX_STREAK})
    new_streak = result.scalar_one_or_none()
    if new_streak is None:
        raise AlreadyClaimedError

    dust, tickets = daily_bonus_reward(new_streak)
    if dust:
        await add_dust(session, user_id=user_id, amount=dust)
        session.add(
            Transaction(
                user_id=user_id, currency=TransactionCurrency.dust, amount=dust, reason=TRANSACTION_REASON_DAILY_BONUS
            )
        )
    if tickets:
        await ticket.grant(session, user_id, tickets)
        session.add(
            Transaction(
                user_id=user_id,
                currency=TransactionCurrency.tickets,
                amount=tickets,
                reason=TRANSACTION_REASON_DAILY_BONUS,
            )
        )

    await session.commit()
    return DailyBonusClaim(day=new_streak, dust=dust, tickets=tickets)


@dataclass
class DailyBonusStatus:
    streak: int  # последний ПОДТВЕРЖДЁННЫЙ день серии (0 — ни разу не забирал)
    claimable: bool
    resets_on_claim: bool  # True — пропущен день, следующий сбор начнёт серию с 1
    seconds_until_claimable: int | None  # None, если claimable уже сейчас


async def get_status(session: AsyncSession, user_id: int) -> DailyBonusStatus | None:
    """Только чтение — для отрисовки экрана ДО нажатия "Забрать" (сама атомарность нужна
    только в claim(), см. выше)."""
    user = await get_by_id(session, user_id)
    if user is None:
        return None

    if user.daily_bonus_claimed_at is None:
        return DailyBonusStatus(streak=0, claimable=True, resets_on_claim=False, seconds_until_claimable=None)

    elapsed = datetime.now(timezone.utc) - user.daily_bonus_claimed_at
    if elapsed >= timedelta(hours=48):
        return DailyBonusStatus(
            streak=user.daily_bonus_streak, claimable=True, resets_on_claim=True, seconds_until_claimable=None
        )
    if elapsed >= timedelta(hours=24):
        return DailyBonusStatus(
            streak=user.daily_bonus_streak, claimable=True, resets_on_claim=False, seconds_until_claimable=None
        )
    remaining = timedelta(hours=24) - elapsed
    return DailyBonusStatus(
        streak=user.daily_bonus_streak,
        claimable=False,
        resets_on_claim=False,
        seconds_until_claimable=int(remaining.total_seconds()),
    )
