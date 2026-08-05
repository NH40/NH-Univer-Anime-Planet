"""Переиспользует те же SQLAlchemy engine/session-фабрику, что и бот (см. CLAUDE.md,
"Стек" -> Mini App: "переиспользует те же SQLAlchemy-модели/БД, что и бот") — общий пакет
`bot.db`, схема не дублируется. API read-only: сюда не должны попадать никакие write-пути,
все мутации остаются только в боте."""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from bot.config.settings import get_settings
from bot.db.session import make_engine, make_session_factory

_settings = get_settings()
engine = make_engine(_settings)
session_factory = make_session_factory(engine)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session
