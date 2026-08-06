from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.base import Base


async def wipe_database(session: AsyncSession) -> None:
    """Полный сброс игровых данных: TRUNCATE всех таблиц приложения одним запросом, схему и
    `alembic_version` не трогаем — миграции переигрывать не нужно, бот сразу работоспособен
    после сброса (см. CLAUDE.md, "Админ-панель"). Список таблиц берём из `Base.metadata`, не
    хардкодим вручную — не разъедется при будущих миграциях. RESTART IDENTITY CASCADE сбрасывает
    автоинкременты и снимает необходимость топологической сортировки по FK вручную."""
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    await session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    await session.commit()
