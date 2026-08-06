from __future__ import annotations

from sqlalchemy import Boolean, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from bot.db.base import Base


class Event(Base):
    """Управляющая запись ивента (см. CLAUDE.md, "Ивенты") — какие ивенты вообще бывают,
    определяет `config/event.EVENT_DEFS` (статичный список), эта таблица хранит только
    переключаемое состояние `is_active`. Строка апсертится лениво при первом переключении
    в /admin (`services/event.set_active`), а не сидируется миграцией заранее.

    `universe_code` НЕ внешний ключ на `universes.code` — под ивент может ещё не быть
    залито ни одной карточки (`assets/cards/event_<code>/...` пока не существует), тогда
    строки в `universes` для него тоже нет. Крутка/коллекция для такого ивента просто
    не находят карт и молча ничего не делают — это ожидаемое состояние "ивент включён,
    но пуст", а не ошибка."""

    __tablename__ = "events"
    __table_args__ = (
        # Максимум один активный ивент одновременно — тот же паттерн, что Season.is_active.
        Index("uq_events_active", "is_active", unique=True, postgresql_where="is_active = true"),
    )

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(64))
    universe_code: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
