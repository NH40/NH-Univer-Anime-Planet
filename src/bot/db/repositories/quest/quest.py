from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from bot.db.models.quest import DailyQuest


async def list_slots(session: AsyncSession, user_id: int) -> list[DailyQuest]:
    result = await session.execute(
        select(DailyQuest).where(DailyQuest.user_id == user_id).order_by(DailyQuest.slot)
    )
    return list(result.scalars().all())


@dataclass
class SlotAssignment:
    slot: int
    quest_code: str
    target: int
    reward_dust: int
    reward_tickets: int


async def assign_slots(session: AsyncSession, *, user_id: int, assignments: list[SlotAssignment]) -> None:
    """Апсерт по (user_id, slot) — та же схема, что `inventory.add_card` (см. CLAUDE.md).
    Каждый слот получает новый quest_code/target/награду и `assigned_at=now()` (прогресс
    для него теперь считается заново с этого момента, см. services/quest/metrics.py), и
    сбрасывается claimed. Не коммитит — коммитит вызывающий сервис."""
    for a in assignments:
        stmt = (
            pg_insert(DailyQuest)
            .values(
                user_id=user_id,
                slot=a.slot,
                quest_code=a.quest_code,
                target=a.target,
                reward_dust=a.reward_dust,
                reward_tickets=a.reward_tickets,
                claimed=False,
                assigned_at=func.now(),
            )
            .on_conflict_do_update(
                index_elements=[DailyQuest.user_id, DailyQuest.slot],
                set_={
                    "quest_code": a.quest_code,
                    "target": a.target,
                    "reward_dust": a.reward_dust,
                    "reward_tickets": a.reward_tickets,
                    "claimed": False,
                    "assigned_at": func.now(),
                },
            )
        )
        await session.execute(stmt)


async def mark_claimed(session: AsyncSession, *, user_id: int, slot: int) -> DailyQuest | None:
    """Атомарно помечает слот забранным ТОЛЬКО если ещё не был забран (см. CLAUDE.md,
    правило 1) — WHERE claimed=false защищает от двойного клика/гонки без отдельного
    Redis-лока на уровне данных (лок в handlers/quest — только UX-предохранитель сверху)."""
    result = await session.execute(
        update(DailyQuest)
        .where(DailyQuest.user_id == user_id, DailyQuest.slot == slot, DailyQuest.claimed.is_(False))
        .values(claimed=True)
        .returning(DailyQuest)
    )
    return result.scalar_one_or_none()


@dataclass
class ClaimAllResult:
    slots: list[int]
    total_dust: int
    total_tickets: int


async def mark_claimed_all(session: AsyncSession, *, user_id: int, slots: list[int]) -> ClaimAllResult:
    """Один UPDATE на все выполненные-но-не-забранные слоты разом (см. CLAUDE.md, правило 3 —
    без Python-цикла по каждому слоту), с тем же WHERE claimed=false предохранителем."""
    if not slots:
        return ClaimAllResult(slots=[], total_dust=0, total_tickets=0)
    result = await session.execute(
        update(DailyQuest)
        .where(DailyQuest.user_id == user_id, DailyQuest.slot.in_(slots), DailyQuest.claimed.is_(False))
        .values(claimed=True)
        .returning(DailyQuest.slot, DailyQuest.reward_dust, DailyQuest.reward_tickets)
    )
    rows = result.all()
    return ClaimAllResult(
        slots=[r.slot for r in rows],
        total_dust=sum(r.reward_dust for r in rows),
        total_tickets=sum(r.reward_tickets for r in rows),
    )
