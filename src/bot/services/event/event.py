from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.event import EVENT_DEFS, EVENT_DEFS_BY_CODE
from bot.db.models.event import Event


class EventNotFoundError(Exception):
    pass


@dataclass
class EventStatus:
    code: str
    title: str
    is_active: bool


async def list_status(session: AsyncSession) -> list[EventStatus]:
    """Всегда ровно `len(EVENT_DEFS)` записей — статус для КАЖДОГО определённого в
    config/event ивента, даже если под него ещё ни разу не переключали (строки в `events`
    ещё нет — тогда просто is_active=False по умолчанию, см. db/models/event.py)."""
    result = await session.execute(select(Event.code, Event.is_active))
    active_by_code = dict(result.all())
    return [
        EventStatus(code=d.code, title=d.title, is_active=active_by_code.get(d.code, False)) for d in EVENT_DEFS
    ]


async def get_active(session: AsyncSession) -> Event | None:
    result = await session.execute(select(Event).where(Event.is_active.is_(True)))
    return result.scalar_one_or_none()


async def set_active(session: AsyncSession, *, code: str, active: bool) -> None:
    """Включает/выключает ивент. Партиционный уникальный индекс `uq_events_active`
    гарантирует не больше одного активного одновременно на уровне БД — поэтому при
    включении сначала гасим ЛЮБОЙ другой активный отдельным `UPDATE` (тот же порядок
    "сначала понизить старого, потом повысить нового", что при передаче владения кланом,
    см. CLAUDE.md), и только потом апсертим/включаем нужную строку."""
    event_def = EVENT_DEFS_BY_CODE.get(code)
    if event_def is None:
        raise EventNotFoundError(code)

    if active:
        await session.execute(update(Event).where(Event.code != code).values(is_active=False))

    stmt = (
        pg_insert(Event)
        .values(code=event_def.code, title=event_def.title, universe_code=event_def.universe_code, is_active=active)
        .on_conflict_do_update(
            index_elements=[Event.code],
            set_={"title": event_def.title, "universe_code": event_def.universe_code, "is_active": active},
        )
    )
    await session.execute(stmt)
    await session.commit()
