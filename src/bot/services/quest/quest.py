from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from bot.config.quest import (
    DAILY_QUEST_ACTIVE_SLOTS,
    DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT,
    DAILY_QUEST_REFRESH_INTERVAL_HOURS,
    QUEST_DEFS_BY_CODE,
)
from bot.constant.quest import TRANSACTION_REASON_QUEST
from bot.db.models.enums import TransactionCurrency
from bot.db.models.quest import DailyQuest
from bot.db.models.transaction import Transaction
from bot.db.models.user import User
from bot.db.repositories import quest as quest_repo
from bot.db.repositories.user import add_dust, get_by_id
from bot.services import ticket
from bot.services.quest.metrics import resolve_progress


class UserNotFoundError(Exception):
    pass


class SlotNotFoundError(Exception):
    pass


class QuestNotDoneError(Exception):
    pass


class QuestAlreadyClaimedError(Exception):
    pass


class NothingToClaimError(Exception):
    pass


class RerollNotAvailableError(Exception):
    pass


@dataclass
class QuestSlotView:
    slot: int
    text: str
    progress: int
    target: int
    reward_dust: int
    reward_tickets: int
    claimed: bool

    @property
    def done(self) -> bool:
        return self.progress >= self.target


@dataclass
class QuestScreenStatus:
    slots: list[QuestSlotView]
    reroll_all_available: bool
    individual_rerolls_left: int


def _pick_codes(count: int, *, exclude: set[str] = frozenset()) -> list[str]:
    pool = [code for code in QUEST_DEFS_BY_CODE if code not in exclude]
    return random.sample(pool, count)


def _assignments(codes: list[str], *, start_slot: int = 0) -> list[quest_repo.SlotAssignment]:
    assignments = []
    for offset, code in enumerate(codes):
        d = QUEST_DEFS_BY_CODE[code]
        assignments.append(
            quest_repo.SlotAssignment(
                slot=start_slot + offset,
                quest_code=code,
                target=d.target,
                reward_dust=d.reward_dust,
                reward_tickets=d.reward_tickets,
            )
        )
    return assignments


async def _refresh(session: AsyncSession, user_id: int) -> list[DailyQuest]:
    """Выдаёт новый набор из DAILY_QUEST_ACTIVE_SLOTS заданий и сбрасывает счётчики
    рероллов — одна логическая операция, один commit (см. CLAUDE.md, правило 10)."""
    codes = _pick_codes(DAILY_QUEST_ACTIVE_SLOTS)
    await quest_repo.assign_slots(session, user_id=user_id, assignments=_assignments(codes))
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            quests_refreshed_at=func.now(),
            daily_quest_reroll_all_used=False,
            daily_quest_individual_reroll_count=0,
        )
    )
    await session.commit()
    return await quest_repo.list_slots(session, user_id)


async def get_status(session: AsyncSession, user_id: int) -> QuestScreenStatus:
    """Читает набор заданий, лениво обновляя его, если прошло DAILY_QUEST_REFRESH_INTERVAL_HOURS
    с прошлого обновления (или заданий ещё не было ни разу) — тот же ленивый паттерн, что у
    войны клана (см. CLAUDE.md, "Кланы"). Прогресс каждого слота — живая агрегация по
    журналу транзакций с момента ЕГО СОБСТВЕННОГО assigned_at (не общего refresh — после
    индивидуального переролла у слота может быть более свежий assigned_at, чем у остальных)."""
    user = await get_by_id(session, user_id)
    if user is None:
        raise UserNotFoundError

    rows = await quest_repo.list_slots(session, user_id)
    stale = datetime.now(timezone.utc) - user.quests_refreshed_at >= timedelta(
        hours=DAILY_QUEST_REFRESH_INTERVAL_HOURS
    )
    if not rows or stale:
        rows = await _refresh(session, user_id)
        user = await get_by_id(session, user_id)

    slots = []
    for row in rows:
        d = QUEST_DEFS_BY_CODE[row.quest_code]
        progress = await resolve_progress(session, user_id=user_id, metric_key=d.metric, since=row.assigned_at)
        slots.append(
            QuestSlotView(
                slot=row.slot,
                text=d.text,
                progress=min(progress, row.target),
                target=row.target,
                reward_dust=row.reward_dust,
                reward_tickets=row.reward_tickets,
                claimed=row.claimed,
            )
        )

    return QuestScreenStatus(
        slots=slots,
        reroll_all_available=not user.daily_quest_reroll_all_used,
        individual_rerolls_left=DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT - user.daily_quest_individual_reroll_count,
    )


@dataclass
class ClaimResult:
    reward_dust: int
    reward_tickets: int


async def claim(session: AsyncSession, *, user_id: int, slot: int) -> ClaimResult:
    """Одна логическая операция — проверка выполнения, пометка "забрано" и начисление
    награды случаются вместе или не случаются вовсе (см. CLAUDE.md, правило 10)."""
    rows = await quest_repo.list_slots(session, user_id)
    row = next((r for r in rows if r.slot == slot), None)
    if row is None:
        raise SlotNotFoundError
    if row.claimed:
        raise QuestAlreadyClaimedError

    d = QUEST_DEFS_BY_CODE[row.quest_code]
    progress = await resolve_progress(session, user_id=user_id, metric_key=d.metric, since=row.assigned_at)
    if progress < row.target:
        raise QuestNotDoneError

    claimed_row = await quest_repo.mark_claimed(session, user_id=user_id, slot=slot)
    if claimed_row is None:
        # Кто-то (повторный клик) уже забрал этот слот между SELECT выше и этим UPDATE —
        # WHERE claimed=false в mark_claimed уже защитил от двойной выдачи (правило 1).
        raise QuestAlreadyClaimedError

    await _grant_reward(session, user_id=user_id, dust=claimed_row.reward_dust, tickets=claimed_row.reward_tickets)
    await session.commit()
    return ClaimResult(reward_dust=claimed_row.reward_dust, reward_tickets=claimed_row.reward_tickets)


@dataclass
class ClaimAllResult:
    count: int
    reward_dust: int
    reward_tickets: int


async def claim_all(session: AsyncSession, *, user_id: int) -> ClaimAllResult:
    rows = await quest_repo.list_slots(session, user_id)
    claimable_slots = []
    for row in rows:
        if row.claimed:
            continue
        d = QUEST_DEFS_BY_CODE[row.quest_code]
        progress = await resolve_progress(session, user_id=user_id, metric_key=d.metric, since=row.assigned_at)
        if progress >= row.target:
            claimable_slots.append(row.slot)

    if not claimable_slots:
        raise NothingToClaimError

    result = await quest_repo.mark_claimed_all(session, user_id=user_id, slots=claimable_slots)
    if not result.slots:
        raise NothingToClaimError

    await _grant_reward(session, user_id=user_id, dust=result.total_dust, tickets=result.total_tickets)
    await session.commit()
    return ClaimAllResult(count=len(result.slots), reward_dust=result.total_dust, reward_tickets=result.total_tickets)


async def _grant_reward(session: AsyncSession, *, user_id: int, dust: int, tickets: int) -> None:
    if dust:
        await add_dust(session, user_id=user_id, amount=dust)
        session.add(
            Transaction(user_id=user_id, currency=TransactionCurrency.dust, amount=dust, reason=TRANSACTION_REASON_QUEST)
        )
    if tickets:
        await ticket.grant(session, user_id, tickets)
        session.add(
            Transaction(
                user_id=user_id, currency=TransactionCurrency.tickets, amount=tickets, reason=TRANSACTION_REASON_QUEST
            )
        )


async def reroll_all(session: AsyncSession, *, user_id: int) -> None:
    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.daily_quest_reroll_all_used.is_(False))
        .values(daily_quest_reroll_all_used=True)
        .returning(User.id)
    )
    if result.scalar_one_or_none() is None:
        raise RerollNotAvailableError

    rows = await quest_repo.list_slots(session, user_id)
    current_codes = {r.quest_code for r in rows}
    codes = _pick_codes(DAILY_QUEST_ACTIVE_SLOTS, exclude=current_codes)
    await quest_repo.assign_slots(session, user_id=user_id, assignments=_assignments(codes))
    await session.commit()


async def reroll_one(session: AsyncSession, *, user_id: int, slot: int) -> None:
    rows = await quest_repo.list_slots(session, user_id)
    if not any(r.slot == slot for r in rows):
        raise SlotNotFoundError

    result = await session.execute(
        update(User)
        .where(User.id == user_id, User.daily_quest_individual_reroll_count < DAILY_QUEST_INDIVIDUAL_REROLL_LIMIT)
        .values(daily_quest_individual_reroll_count=User.daily_quest_individual_reroll_count + 1)
        .returning(User.id)
    )
    if result.scalar_one_or_none() is None:
        raise RerollNotAvailableError

    current_codes = {r.quest_code for r in rows}
    new_code = _pick_codes(1, exclude=current_codes)[0]
    await quest_repo.assign_slots(session, user_id=user_id, assignments=_assignments([new_code], start_slot=slot))
    await session.commit()
