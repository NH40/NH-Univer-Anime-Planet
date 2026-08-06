from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from bot.db.base import Base


class DailyQuest(Base):
    """Один из 5 активных слотов ежедневных заданий игрока (см. CLAUDE.md, "Ежедневные
    задания"). `target`/`reward_*` — снимок значений из `config/quest` НА МОМЕНТ выдачи
    задания, а не живая ссылка на конфиг — если баланс поменяют в конфиге, уже выданные,
    но ещё не забранные задания игрока не должны измениться задним числом. Прогресс не
    хранится отдельной колонкой — считается на лету по журналу `transactions` начиная с
    `assigned_at` (см. services/quest/metrics.py), тот же принцип "живая агрегация", что и
    у UBP клана/прогресса войны."""

    __tablename__ = "daily_quests"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    slot: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    quest_code: Mapped[str] = mapped_column(String(64))
    target: Mapped[int] = mapped_column(Integer)
    reward_dust: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    reward_tickets: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    claimed: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
