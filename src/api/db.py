"""Переиспользует те же SQLAlchemy engine/session-фабрику, что и бот (см. CLAUDE.md,
"Стек" -> Mini App: "переиспользует те же SQLAlchemy-модели/БД, что и бот") — общий пакет
`bot.db`, схема не дублируется. API в основном read-only, но с 2026-08-08 есть ОДНО
исключение — `POST /api/battle-pass/claim` (см. CLAUDE.md, "Mini App", и
`api/routers/battle_pass.py`), сознательная и подтверждённая пользователем смена границы,
а не случайное нарушение. Любой новый write-путь сверх этого — тоже осознанное решение,
не default."""

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
